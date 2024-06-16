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
# noinspection Mypy
import redis
from redis import ConnectionError, ConnectionPool, Redis, RedisError, TimeoutError

from ._base import BaseStrictRedis, EXPIRED, SESSION_EXPIRED, Session
from .err import FuncArgsError, RedisClientError, RedisConnectError, RedisTimeoutError
from .utils import ignore_error, ordumps, orloads

__all__ = ("RdbClient",)


class RdbClient(BaseStrictRedis, Redis):
    """
    redis 工具类
    """

    def __init__(self, app=None, *, host: str = "127.0.0.1", port: int = 6379, dbname: int = 0, passwd: str = "",
                 pool_size: int = 25, connect_timeout: int = 10, **kwargs) -> None:
        """
        redis 工具类
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

        kwargs.setdefault("socket_connect_timeout", connect_timeout)
        self.kwargs: Dict[str, Any] = kwargs

        super().__init__(app, host=host, port=port, dbname=dbname, passwd=passwd, pool_size=pool_size)

    def init_app(self, app) -> None:
        """
        redis 工具类
        Args:
            app: app应用
        Returns:

        """
        super().init_app(app)

        # 初始化连接
        self.open_connection()
        # 注册退出方法
        if getattr(app, "on_event", None):  # 适配fastapi
            app.on_event('shutdown')(self.close_connection)
        else:
            atexit.register(self.close_connection)

    # noinspection DuplicatedCode
    def init_engine(self, *, host: str = "127.0.0.1", port: int = 6379, dbname: int = 0, passwd: str = "",
                    pool_size: int = 25, connect_timeout: int = 10, **kwargs) -> None:
        """
        redis 工具类
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
        kwargs.setdefault("socket_connect_timeout", connect_timeout)
        self.kwargs.update(kwargs)
        super().init_engine(host=host, port=port, dbname=dbname, passwd=passwd, pool_size=pool_size)

        # 初始化连接
        self.open_connection()
        # 注册退出方法
        atexit.register(self.close_connection)

    def open_connection(self, ):
        """

        Args:

        Returns:

        """
        # 返回值都做了解码，应用层不需要再decode
        self.pool = redis.ConnectionPool(host=self.host, port=self.port, db=self.dbname, password=self.passwd,
                                         decode_responses=True, max_connections=self.pool_size, **self.kwargs)
        super(BaseStrictRedis, self).__init__(connection_pool=self.pool, decode_responses=True)

    def close_connection(self, ):
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

    def save_session(self, session: Session, ex: int = SESSION_EXPIRED) -> str:
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
            self.hset(session.session_id, mapping=self.rs_dumps(session.to_dict()))
            self.expire(session.session_id, ex)
        # 清除老的令牌
        old_session_id = self.get_usual_data(session.account_id)
        if old_session_id:
            with ignore_error():
                self.delete_session(str(old_session_id))
        # 更新新的令牌
        self.save_usual_data(session.account_id, session.session_id, ex=ex)

        return session.session_id

    def delete_session(self, session_id: str) -> None:
        """
        利用hash map删除session
        Args:
            session_id: session id
        Returns:

        """

        with self.catch_error():
            session_data = self.get_session(session_id)
        if session_data:
            with ignore_error():  # 删除已经存在的和账户相关的缓存key
                self.delete_keys(self._get_session_keys(session_data))

    def update_session(self, session: Session, ex: int = SESSION_EXPIRED) -> None:
        """
        利用hash map更新session
        Args:
            session: Session实例
            ex: 过期时间，单位秒
        Returns:

        """
        with self.catch_error():
            self.hset(session.session_id, mapping=self.rs_dumps(session.to_dict()))
            self.expire(session.session_id, ex)
            self.expire(session.account_id, ex)
        # 更新令牌
        self.save_hash_data(session.account_id, session.session_id, ex=ex)

    def get_session(self, session_id: str, ex: int = SESSION_EXPIRED) -> Optional[Session]:
        """
        获取session
        Args:
            session_id: session id
            ex: 过期时间，单位秒
        Returns:

        """
        session_value = None
        with self.catch_error():
            session_data = self.hgetall(session_id)
            if session_data:
                self.expire(session_id, ex)
                session_data = self.rs_loads(session_data)
                self.expire(session_data["account_id"], ex)
                session_value = Session(session_data.pop('account_id'), **session_data)
        return session_value

    def verify(self, session_id: str) -> Session:
        """
        校验session，主要用于登录校验
        Args:
            session_id
        Returns:

        """
        session = self.get_session(session_id)
        if not session:
            raise RedisClientError("invalid session_id, session_id={}".format(session_id))
        return session

    # noinspection DuplicatedCode
    def save_hash_data(self, name: str, hash_data: Any, field_name: str = "", ex: int = EXPIRED) -> None:
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
                self.hset(name, field_name, hash_data if isinstance(hash_data, str) else ordumps(hash_data))
            else:
                if not isinstance(hash_data, Dict):
                    raise ValueError("hash data error, must be MutableMapping.")
                # 是否对每个键值进行dump
                self.hset(name, mapping=self.rs_dumps(hash_data))
            # 设置过期时间
            self.expire(name, ex)

    def get_hash_data(self, name: str, field_name: str = "", ex: int = EXPIRED) -> Any:
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
                hash_data = self.hget(name, field_name)
                if hash_data:
                    hash_data = orloads(hash_data)
            else:
                hash_data = self.hgetall(name)
                if hash_data:
                    hash_data = self.rs_loads(hash_data)
            # 设置过期时间
            self.expire(name, ex)

        return hash_data

    def get_list_data(self, name: str, start: int = 0, end: int = -1, ex: int = EXPIRED
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
            data = self.lrange(name, start=start, end=end)
            if data:
                self.expire(name, ex)

        return data

    def save_list_data(self, name: str, list_data: Union[List[Union[str, int, float]], Union[str, int, float]],
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
                self.lpush(name, *list_data)
            else:
                self.rpush(name, *list_data)
            # 设置过期时间
            self.expire(name, ex)

    def save_usual_data(self, name: str, value: Any, ex: int = EXPIRED) -> None:
        """
        保存列表、映射对象为普通的字符串
        Args:
            name: redis key的名称
            value: 保存的值，可以是可序列化的任何职
            ex: 过期时间，单位秒
        Returns:

        """
        with self.catch_error():
            self.set(name, ordumps(value) if not isinstance(value, str) else value, ex)

    def get_usual_data(self, name: str, ex: int = EXPIRED) -> Any:
        """
        获取name对应的值
        Args:
            name: redis key的名称
            ex: 过期时间，单位秒
        Returns:
            反序列化对象
        """
        with self.catch_error():
            data = self.get(name)
            if data:  # 保证key存在时设置过期时间
                self.expire(name, ex)
                data = orloads(data)

        return data

    def incrbynumber(self, name: str, amount: int = 1, ex: int = EXPIRED) -> None:
        """
        通过给定的值对已有的值进行递增
        Args:

        Returns:

        """
        with self.catch_error():
            if isinstance(amount, int):
                self.incr(name, amount)
            else:
                self.incrbyfloat(name, amount)
            # 增加过期时间
            self.expire(name, ex)

    def is_exists(self, name: str) -> bool:
        """
        判断redis key是否存在
        Args:
            name: redis key的名称
        Returns:

        """
        with self.catch_error():
            rs = self.exists(name)
        return True if rs else False

    def delete_keys(self, names: Sequence[str]) -> None:
        """
        删除一个或多个redis key
        Args:
            names: redis key的名称
        Returns:

        """
        names = (names,) if isinstance(names, str) else names
        with self.catch_error():
            self.delete(*names)

    def get_keys(self, pattern_name: str) -> List[str]:
        """
        根据正则表达式获取redis的keys
        Args:
            pattern_name:正则表达式的名称
        Returns:

        """
        with self.catch_error():
            rs = self.keys(pattern_name)
        return rs

    def memory_help(self, **kwargs):
        """memory_help"""
        pass

    def memory_doctor(self, **kwargs):
        """memory_doctor"""
        pass

    def debug_segfault(self, **kwargs):
        """debug_segfault"""
        pass

    def script_debug(self, *args):
        """script_debug"""
        pass

    def command_info(self, **kwargs):
        """command_info"""
        pass
