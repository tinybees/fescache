#!/usr/bin/env python3
# coding=utf-8

"""
@author: guoyanfeng
@software: PyCharm
@time: 18-12-25 下午5:15
"""
import atexit
from contextlib import contextmanager
from typing import Any, Dict, Generator, List, Optional, Sequence, Union

import aelog
from aredis import ConnectionError, ConnectionPool, RedisError, StrictRedis, TimeoutError
from aredis.commands.cluster import ClusterCommandMixin
from aredis.commands.connection import ConnectionCommandMixin
from aredis.commands.extra import ExtraCommandMixin
from aredis.commands.geo import GeoCommandMixin
from aredis.commands.hash import HashCommandMixin
from aredis.commands.hyperlog import HyperLogCommandMixin
from aredis.commands.iter import IterCommandMixin
from aredis.commands.keys import KeysCommandMixin
from aredis.commands.lists import ListsCommandMixin
from aredis.commands.pubsub import PubSubCommandMixin
from aredis.commands.scripting import ScriptingCommandMixin
from aredis.commands.sentinel import SentinelCommandMixin
from aredis.commands.server import ServerCommandMixin
from aredis.commands.sets import SetsCommandMixin
from aredis.commands.sorted_set import SortedSetCommandMixin
from aredis.commands.streams import StreamsCommandMixin
from aredis.commands.strings import StringsCommandMixin
from aredis.commands.transaction import TransactionCommandMixin

from ._base import BaseStrictRedis, EXPIRED, SESSION_EXPIRED, Session
from .err import FuncArgsError, RedisClientError, RedisConnectError, RedisTimeoutError
from .utils import ignore_error, ordumps, orloads

__all__ = ("AIORdbClient",)


class AIORdbClient(BaseStrictRedis, StrictRedis, ClusterCommandMixin, ConnectionCommandMixin,
                   ExtraCommandMixin, GeoCommandMixin, HashCommandMixin, HyperLogCommandMixin,
                   KeysCommandMixin, ListsCommandMixin, PubSubCommandMixin,
                   ScriptingCommandMixin, SentinelCommandMixin, ServerCommandMixin,
                   SetsCommandMixin, SortedSetCommandMixin, StringsCommandMixin,
                   TransactionCommandMixin, StreamsCommandMixin, IterCommandMixin):
    """
    redis 非阻塞工具类
    """

    def __init__(self, app=None, *, host: str = "127.0.0.1", port: int = 6379, dbname: int = 0, passwd: str = "",
                 pool_size: int = 25, connect_timeout: int = 10, **kwargs) -> None:
        """
        redis 非阻塞工具类
        Args:
            app: app应用
            host:redis host
            port:redis port
            dbname: database name
            passwd: redis password
            pool_size: redis pool size
            connect_timeout: 连接超时时间
            kwargs: other kwargs
        """
        self.pool: Optional[ConnectionPool] = None

        kwargs.setdefault("connect_timeout", connect_timeout)
        self.kwargs: Dict[str, Any] = kwargs

        super().__init__(app, host=host, port=port, dbname=dbname, passwd=passwd, pool_size=pool_size)

    def init_app(self, app) -> None:
        """
        redis 非阻塞工具类
        Args:
            app: app应用
        Returns:

        """
        super().init_app(app)

        # noinspection PyUnusedLocal
        @app.listener('before_server_start')
        async def open_connection(app_, loop):
            """

            Args:

            Returns:

            """
            # 返回值都做了解码，应用层不需要再decode
            self.pool = ConnectionPool(host=self.host, port=self.port, db=self.dbname, password=self.passwd,
                                       decode_responses=True, max_connections=self.pool_size, **self.kwargs)
            super(BaseStrictRedis, self).__init__(connection_pool=self.pool, decode_responses=True)

        # noinspection PyUnusedLocal
        @app.listener('after_server_stop')
        async def close_connection(app_, loop):
            """
            释放redis连接池所有连接
            Args:

            Returns:

            """
            if self.pool:
                self.pool.disconnect()
            aelog.debug("清理redis连接池完毕！")

    # noinspection DuplicatedCode
    def init_engine(self, *, host: str = "127.0.0.1", port: int = 6379, dbname: int = 0, passwd: str = "",
                    pool_size: int = 25, connect_timeout: int = 10, **kwargs) -> None:
        """
        redis 非阻塞工具类
        Args:
            host:redis host
            port:redis port
            dbname: database name
            passwd: redis password
            pool_size: redis pool size
            connect_timeout: 连接超时时间
            kwargs: other kwargs
        Returns:

        """
        kwargs.setdefault("connect_timeout", connect_timeout)
        self.kwargs.update(kwargs)
        super().init_engine(host=host, port=port, dbname=dbname, passwd=passwd, pool_size=pool_size)

        # 返回值都做了解码，应用层不需要再decode
        self.pool = ConnectionPool(host=self.host, port=self.port, db=self.dbname, password=self.passwd,
                                   decode_responses=True, max_connections=self.pool_size, **self.kwargs)
        super(BaseStrictRedis, self).__init__(connection_pool=self.pool, decode_responses=True)

        @atexit.register
        def close_connection():
            """
            释放redis连接池所有连接
            Args:

            Returns:

            """
            if self.pool:
                self.pool.disconnect()
            aelog.debug("清理redis连接池完毕！")

    @contextmanager
    def catch_error(self, ) -> Generator[None, None, None]:
        """

        Args:

        Returns:

        """
        try:
            yield
        except ConnectionError as e:
            aelog.exception(e)
            raise RedisConnectError("Redis连接错误,请检查连接参数是否正确.")
        except TimeoutError as e:
            aelog.exception(e)
            raise RedisTimeoutError("Redis超时错误,请检查连接参数是否正确.")
        except RedisError as e:
            aelog.exception(e)
            raise RedisClientError("Redis其他错误,请检查.")

    async def save_session(self, session: Session, ex: int = SESSION_EXPIRED) -> str:
        """
        利用hash map保存session
        Args:
            session: Session 实例
            ex: 过期时间，单位秒
        Returns:

        """
        if not isinstance(session, Session):
            raise FuncArgsError(f"session value error, must be Session Type.")

        with self.catch_error():
            await self.hmset(session.session_id, self.rs_dumps(session.to_dict()))
            await self.expire(session.session_id, ex)
        # 清除老的令牌
        old_session_id = await self.get_usual_data(session.account_id)
        if old_session_id:
            with ignore_error():
                await self.delete_session(str(old_session_id))
        # 更新新的令牌
        await self.save_usual_data(session.account_id, session.session_id, ex=ex)

        return session.session_id

    async def delete_session(self, session_id: str) -> None:
        """
        利用hash map删除session
        Args:
            session_id: session id
        Returns:

        """

        with self.catch_error():
            session_data = await self.get_session(session_id)
        if session_data:
            with ignore_error():  # 删除已经存在的和账户相关的缓存key
                await self.delete_keys(self._get_session_keys(session_data))

    async def update_session(self, session: Session, ex: int = SESSION_EXPIRED) -> None:
        """
        利用hash map更新session
        Args:
            session: Session实例
            ex: 过期时间，单位秒
        Returns:

        """
        with self.catch_error():
            await self.hmset(session.session_id, self.rs_dumps(session.to_dict()))
            await self.expire(session.session_id, ex)
            await self.expire(session.account_id, ex)
        # 更新令牌
        await self.save_usual_data(session.account_id, session.session_id, ex=ex)

    async def get_session(self, session_id: str, ex: int = SESSION_EXPIRED) -> Optional[Session]:
        """
        获取session
        Args:
            session_id: session id
            ex: 过期时间，单位秒
        Returns:

        """
        session_value = None
        with self.catch_error():
            session_data = await self.hgetall(session_id)
            if session_data:
                await self.expire(session_id, ex)
                session_data = self.rs_loads(session_data)
                await self.expire(session_data["account_id"], ex)
                session_value = Session(session_data.pop('account_id'), **session_data)
        return session_value

    async def verify(self, session_id: str) -> Session:
        """
        校验session，主要用于登录校验
        Args:
            session_id
        Returns:

        """
        session = await self.get_session(session_id)
        if not session:
            raise RedisClientError("invalid session_id, session_id={}".format(session_id))
        return session

    # noinspection DuplicatedCode
    async def save_hash_data(self, name: str, hash_data: Any, field_name: str = "", ex: int = EXPIRED) -> None:
        """
        获取hash对象field_name对应的值
        Args:
            name: redis hash key的名称
            field_name: 保存的hash mapping 中的某个字段
            hash_data: 获取的hash对象中属性的名称
            ex: 过期时间，单位秒
        Returns:
            反序列化对象
        """
        with self.catch_error():
            if field_name:
                await self.hset(name, field_name, hash_data if isinstance(hash_data, str) else ordumps(hash_data))
            else:
                if not isinstance(hash_data, Dict):
                    raise ValueError("hash data error, must be MutableMapping.")
                # 是否对每个键值进行dump
                await self.hmset(name, self.rs_dumps(hash_data))
            # 设置过期时间
            await self.expire(name, ex)

    async def get_hash_data(self, name: str, field_name: str = "", ex: int = EXPIRED) -> Any:
        """
        获取hash对象field_name对应的值
        Args:
            name: redis hash key的名称
            field_name: 获取的hash对象中属性的名称
            ex: 过期时间，单位秒
        Returns:
            反序列化对象
        """
        with self.catch_error():
            if field_name:
                hash_data = await self.hget(name, field_name)
                if hash_data:
                    hash_data = orloads(hash_data)
            else:
                hash_data = await self.hgetall(name)
                if hash_data:
                    hash_data = self.rs_loads(hash_data)
            # 设置过期时间
            await self.expire(name, ex)

        return hash_data

    async def get_list_data(self, name: str, start: int = 0, end: int = -1, ex: int = EXPIRED
                            ) -> Optional[List[Union[str, int, float]]]:
        """
        获取redis的列表中的数据
        Args:
            name: redis key的名称
            start: 获取数据的起始位置,默认列表的第一个值
            end: 获取数据的结束位置，默认列表的最后一个值
            ex: 过期时间，单位秒
        Returns:

        """
        with self.catch_error():
            data = await self.lrange(name, start=start, end=end)
            if data:
                await self.expire(name, ex)

        return data

    async def save_list_data(self, name: str, list_data: Union[List[Union[str, int, float]], Union[str, int, float]],
                             save_to_left: bool = True, ex: int = EXPIRED) -> None:
        """
        保存数据到redis的列表中
        Args:
            name: redis key的名称
            list_data: 保存的值,可以是单个值也可以是元祖
            save_to_left: 是否保存到列表的左边，默认保存到左边
            ex: 过期时间，单位秒
        Returns:

        """
        list_data = [list_data] if isinstance(list_data, str) else list_data
        with self.catch_error():
            if save_to_left:
                await self.lpush(name, *list_data)
            else:
                await self.rpush(name, *list_data)
            # 设置过期时间
            await self.expire(name, ex)

    async def save_usual_data(self, name: str, value: Any, ex: int = EXPIRED) -> None:
        """
        保存列表、映射对象为普通的字符串
        Args:
            name: redis key的名称
            value: 保存的值，可以是可序列化的任何职
            ex: 过期时间，单位秒
        Returns:

        """
        with self.catch_error():
            await self.set(name, ordumps(value) if not isinstance(value, str) else value, ex)

    async def get_usual_data(self, name: str, ex: int = EXPIRED) -> Any:
        """
        获取name对应的值
        Args:
            name: redis key的名称
            ex: 过期时间，单位秒
        Returns:
            反序列化对象
        """
        with self.catch_error():
            data = await self.get(name)
            if data:  # 保证key存在时设置过期时间
                await self.expire(name, ex)
                data = orloads(data)

        return data

    async def incrbynumber(self, name: str, amount: int = 1, ex: int = EXPIRED) -> None:
        """
        通过给定的值对已有的值进行递增
        Args:

        Returns:

        """
        with self.catch_error():
            if isinstance(amount, int):
                await self.incr(name, amount)
            else:
                await self.incrbyfloat(name, amount)
            # 增加过期时间
            await self.expire(name, ex)

    async def is_exists(self, name: str) -> bool:
        """
        判断redis key是否存在
        Args:
            name: redis key的名称
        Returns:

        """
        with self.catch_error():
            rs = await self.exists(name)
        return True if rs else False

    async def delete_keys(self, names: Sequence[str]) -> None:
        """
        删除一个或多个redis key
        Args:
            names: redis key的名称
        Returns:

        """
        names = (names,) if isinstance(names, str) else names
        with self.catch_error():
            await self.delete(*names)

    async def get_keys(self, pattern_name: str) -> List[str]:
        """
        根据正则表达式获取redis的keys
        Args:
            pattern_name:正则表达式的名称
        Returns:

        """
        with self.catch_error():
            rs = await self.keys(pattern_name)
        return rs
