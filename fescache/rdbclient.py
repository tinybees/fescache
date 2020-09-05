#!/usr/bin/env python3
# coding=utf-8

"""
@author: guoyanfeng
@software: PyCharm
@time: 18-12-25 下午5:15
"""
import atexit
from collections import MutableMapping
from typing import Any, Dict, List, NoReturn, Optional, Union

import aelog
import redis
import ujson
from redis import RedisError

from ._base import BaseRdbClient, EXPIRED, LONG_EXPIRED, SESSION_EXPIRED, Session
from .err import RedisClientError
from .utils import ignore_error

__all__ = ("RdbClient",)


class RdbClient(BaseRdbClient):
    """
    redis 工具类
    """

    def __init__(self, app=None, *, host: str = "127.0.0.1", port: int = 6379, dbname: int = 0, passwd: str = "",
                 pool_size: int = 50):
        """
        redis 工具类
        Args:
            app: app应用
            host:redis host
            port:redis port
            dbname: database name
            passwd: redis password
            pool_size: redis pool size
        """
        self.pool: Optional[redis.ConnectionPool] = None
        self.redis_db: Optional[redis.StrictRedis] = None

        super().__init__(app, host=host, port=port, dbname=dbname, passwd=passwd, pool_size=pool_size)

    def init_app(self, app, *, host: str = None, port: int = None, dbname: int = None, passwd: str = "",
                 pool_size: int = None):
        """
        redis 工具类
        Args:
            app: app应用
            host:redis host
            port:redis port
            dbname: database name
            passwd: redis password
            pool_size: redis pool size
        Returns:

        """
        super().init_app(app, host=host, port=port, dbname=dbname, passwd=passwd, pool_size=pool_size)

        @app.before_first_request
        def open_connection():
            """

            Args:

            Returns:

            """
            # 返回值都做了解码，应用层不需要再decode
            self.pool = redis.ConnectionPool(host=host, port=port, db=dbname, password=passwd, decode_responses=True,
                                             max_connections=pool_size)
            self.redis_db = redis.StrictRedis(connection_pool=self.pool, decode_responses=True)

        @atexit.register
        def close_connection():
            """
            释放redis连接池所有连接
            Args:

            Returns:

            """
            self.redis_db = None
            if self.pool:
                self.pool.disconnect()

    # noinspection DuplicatedCode
    def init_engine(self, *, host: str = None, port: int = None, dbname: int = None, passwd: str = "",
                    pool_size: int = None):
        """
        redis 工具类
        Args:
            host:redis host
            port:redis port
            dbname: database name
            passwd: redis password
            pool_size: redis pool size
        Returns:

        """
        super().init_engine(host=host, port=port, dbname=dbname, passwd=passwd, pool_size=pool_size)
        # 返回值都做了解码，应用层不需要再decode
        self.pool = redis.ConnectionPool(host=host, port=port, db=dbname, password=passwd, decode_responses=True,
                                         max_connections=pool_size)
        self.redis_db = redis.StrictRedis(connection_pool=self.pool, decode_responses=True)

        @atexit.register
        def close_connection():
            """
            释放redis连接池所有连接
            Args:

            Returns:

            """
            self.redis_db = None
            if self.pool:
                self.pool.disconnect()

    def save_session(self, session: Session, dump_responses: bool = False, ex: int = SESSION_EXPIRED) -> str:
        """
        利用hash map保存session
        Args:
            session: Session 实例
            dump_responses: 是否对每个键值进行dump
            ex: 过期时间，单位秒
        Returns:

        """
        session_data = self.response_dumps(dump_responses, session)

        try:
            if not self.redis_db.hmset(session_data["session_id"], session_data):
                raise RedisClientError("save session failed, session_id={}".format(session_data["session_id"]))
            if not self.redis_db.expire(session_data["session_id"], ex):
                aelog.error("set session expire failed, session_id={}".format(session_data["session_id"]))
        except RedisError as e:
            aelog.exception("save session error: {}, {}".format(session.session_id, e))
            raise RedisClientError(str(e))
        else:
            # 清除老的令牌
            try:
                old_session_id = self.get_hash_data(self._account_key, field_name=session.account_id)
            except RedisClientError as e:
                aelog.info(f"{session.account_id} no old token token, {str(e)}")
            else:
                with ignore_error():
                    self.delete_session(old_session_id, False)
            # 更新新的令牌
            self.save_update_hash_data(self._account_key, field_name=session.account_id,
                                       hash_data=session.session_id, ex=LONG_EXPIRED)
            return session.session_id

    def delete_session(self, session_id: str, delete_key: bool = True) -> NoReturn:
        """
        利用hash map删除session
        Args:
            session_id: session id
            delete_key: 删除account到session的account key
        Returns:

        """

        try:
            session_id_ = self.redis_db.hget(session_id, "session_id")
            if session_id_ != session_id:
                raise RedisClientError("invalid session_id, session_id={}".format(session_id))
            exist_keys = []
            session_data = self.get_session(session_id, cls_flag=False)
            exist_keys.append(session_data["org_id"])
            exist_keys.append(session_data["role_id"])
            exist_keys.append(session_data["permission_id"])
            exist_keys.append(session_data["static_permission_id"])
            exist_keys.append(session_data["dynamic_permission_id"])
            exist_keys.append(session_data["page_id"])
            exist_keys.append(session_data["page_menu_id"])

            with ignore_error():  # 删除已经存在的和账户相关的缓存key
                self.delete_keys(exist_keys)
                if delete_key is True:
                    self.redis_db.hdel(self._account_key, session_data["account_id"])

            if not self.redis_db.delete(session_id):
                aelog.error("delete session failed, session_id={}".format(session_id))
        except RedisError as e:
            aelog.exception("delete session error: {}, {}".format(session_id, e))
            raise RedisClientError(str(e))

    def update_session(self, session: Session, dump_responses: bool = False, ex: int = SESSION_EXPIRED) -> NoReturn:
        """
        利用hash map更新session
        Args:
            session: Session实例
            ex: 过期时间，单位秒
            dump_responses: 是否对每个键值进行dump
        Returns:

        """
        session_data = self.response_dumps(dump_responses, session)

        try:
            if not self.redis_db.hmset(session_data["session_id"], session_data):
                raise RedisClientError("update session failed, session_id={}".format(session_data["session_id"]))
            if not self.redis_db.expire(session_data["session_id"], ex):
                aelog.error("set session expire failed, session_id={}".format(session_data["session_id"]))
        except RedisError as e:
            aelog.exception("update session error: {}, {}".format(session_data["session_id"], e))
            raise RedisClientError(str(e))
        else:
            # 更新令牌
            self.save_update_hash_data(self._account_key, field_name=session.account_id,
                                       hash_data=session.session_id, ex=LONG_EXPIRED)

    def get_session(self, session_id: str, ex: int = SESSION_EXPIRED, cls_flag: bool = True,
                    load_responses: bool = False) -> Union[Session, Dict[str, str]]:
        """
        获取session
        Args:
            session_id: session id
            ex: 过期时间，单位秒
            cls_flag: 是否返回session的类实例
            load_responses: 结果的键值是否进行load
        Returns:

        """

        try:
            session_data = self.redis_db.hgetall(session_id)
            if not session_data:
                raise RedisClientError("not found session, session_id={}".format(session_id))

            if not self.redis_db.expire(session_id, ex):
                aelog.error("set session expire failed, session_id={}".format(session_id))
        except RedisError as e:
            aelog.exception("get session error: {}, {}".format(session_id, e))
            raise RedisClientError(e)
        else:
            # 返回的键值对是否做load
            if load_responses:
                hash_data = {}
                for hash_key, hash_val in session_data.items():
                    with ignore_error():
                        hash_val = ujson.loads(hash_val)
                    hash_data[hash_key] = hash_val
                session_data = hash_data

            if cls_flag:
                return Session(session_data.pop('account_id'), session_id=session_data.pop('session_id'),
                               org_id=session_data.pop("org_id"), role_id=session_data.pop("role_id"),
                               permission_id=session_data.pop("permission_id"), **session_data)
            else:
                return session_data

    def verify(self, session_id: str) -> Session:
        """
        校验session，主要用于登录校验
        Args:
            session_id
        Returns:

        """
        try:
            session = self.get_session(session_id)
        except RedisClientError as e:
            raise RedisClientError(str(e))
        else:
            if not session:
                raise RedisClientError("invalid session_id, session_id={}".format(session_id))
            return session

    def save_update_hash_data(self, name: str, hash_data: Dict, field_name: str = None, dump_responses: bool = False,
                              ex: int = EXPIRED) -> str:
        """
        获取hash对象field_name对应的值
        Args:
            name: redis hash key的名称
            field_name: 保存的hash mapping 中的某个字段
            hash_data: 获取的hash对象中属性的名称
            ex: 过期时间，单位秒
            dump_responses: 是否对每个键值进行dump
        Returns:
            反序列化对象
        """
        if field_name is None and not isinstance(hash_data, MutableMapping):
            raise ValueError("hash data error, must be MutableMapping.")

        try:
            if not field_name:
                # 是否对每个键值进行dump
                if dump_responses:
                    rs_data = {}
                    for hash_key, hash_val in hash_data.items():
                        if not isinstance(hash_val, str):
                            with ignore_error():
                                hash_val = ujson.dumps(hash_val)
                        rs_data[hash_key] = hash_val
                    hash_data = rs_data

                if not self.redis_db.hmset(name, hash_data):
                    raise RedisClientError("save hash data mapping failed, session_id={}".format(name))
            else:
                hash_data = hash_data if isinstance(hash_data, str) else ujson.dumps(hash_data)
                self.redis_db.hset(name, field_name, hash_data)

            if not self.redis_db.expire(name, ex):
                aelog.error("set hash data expire failed, session_id={}".format(name))
        except RedisError as e:
            raise RedisClientError(str(e))
        else:
            return name

    def get_hash_data(self, name: str, field_name: str = None, load_responses: bool = False,
                      ex: int = EXPIRED) -> Dict:
        """
        获取hash对象field_name对应的值
        Args:
            name: redis hash key的名称
            field_name: 获取的hash对象中属性的名称
            ex: 过期时间，单位秒
            load_responses: 结果的键值是否进行load
        Returns:
            反序列化对象
        """
        try:
            if field_name:
                hash_data = self.redis_db.hget(name, field_name)
                # 返回的键值对是否做load
                if load_responses:
                    with ignore_error():
                        hash_data = ujson.loads(hash_data)
            else:
                hash_data = self.redis_db.hgetall(name)
                # 返回的键值对是否做load
                if load_responses:
                    rs_data = {}
                    for hash_key, hash_val in hash_data.items():
                        with ignore_error():
                            hash_val = ujson.loads(hash_val)
                        rs_data[hash_key] = hash_val
                    hash_data = rs_data
            if not hash_data:
                raise RedisClientError("not found hash data, name={}, field_name={}".format(name, field_name))

            if not self.redis_db.expire(name, ex):
                aelog.error("set expire failed, name={}".format(name))
        except RedisError as e:
            raise RedisClientError(str(e))
        else:
            return hash_data

    def get_list_data(self, name: str, start: int = 0, end: int = -1, ex: int = EXPIRED) -> List:
        """
        获取redis的列表中的数据
        Args:
            name: redis key的名称
            start: 获取数据的起始位置,默认列表的第一个值
            end: 获取数据的结束位置，默认列表的最后一个值
            ex: 过期时间，单位秒
        Returns:

        """
        try:
            data = self.redis_db.lrange(name, start=start, end=end)
            if not self.redis_db.expire(name, ex):
                aelog.error("set expire failed, name={}".format(name))
        except RedisError as e:
            raise RedisClientError(str(e))
        else:
            return data

    def save_list_data(self, name: str, list_data: Union[List, str], save_to_left: bool = True,
                       ex: int = EXPIRED) -> str:
        """
        保存数据到redis的列表中
        Args:
            name: redis key的名称
            list_data: 保存的值,可以是单个值也可以是元祖
            save_to_left: 是否保存到列表的左边，默认保存到左边
            ex: 过期时间，单位秒
        Returns:

        """
        list_data = (list_data,) if isinstance(list_data, str) else list_data
        try:
            if save_to_left:
                if not self.redis_db.lpush(name, *list_data):
                    raise RedisClientError("lpush value to head failed.")
            else:
                if not self.redis_db.rpush(name, *list_data):
                    raise RedisClientError("lpush value to tail failed.")
            if not self.redis_db.expire(name, ex):
                aelog.error("set expire failed, name={}".format(name))
        except RedisError as e:
            raise RedisClientError(str(e))
        else:
            return name

    def save_update_usual_data(self, name: str, value: Any, ex: int = EXPIRED) -> str:
        """
        保存列表、映射对象为普通的字符串
        Args:
            name: redis key的名称
            value: 保存的值，可以是可序列化的任何职
            ex: 过期时间，单位秒
        Returns:

        """
        value = ujson.dumps(value) if not isinstance(value, str) else value
        try:
            if not self.redis_db.set(name, value, ex):
                raise RedisClientError("set serializable value failed!")
        except RedisError as e:
            raise RedisClientError(str(e))
        else:
            return name

    def incrbynumber(self, name: str, amount: int = 1, ex: int = EXPIRED) -> str:
        """

        Args:

        Returns:

        """
        try:
            if isinstance(amount, int):
                if not self.redis_db.incr(name, amount):
                    raise RedisClientError("Increments int value failed!")
            else:
                if not self.redis_db.incrbyfloat(name, amount):
                    raise RedisClientError("Increments float value failed!")
            if not self.redis_db.expire(name, ex):
                aelog.error("set expire failed, name={}".format(name))
        except RedisError as e:
            raise RedisClientError(str(e))
        else:
            return name

    def get_usual_data(self, name: str, load_responses: bool = True, update_expire: bool = True,
                       ex: int = EXPIRED) -> Union[Dict, str]:
        """
        获取name对应的值
        Args:
            name: redis key的名称
            load_responses: 是否转码默认转码
            update_expire: 是否更新过期时间
            ex: 过期时间，单位秒
        Returns:
            反序列化对象
        """
        data = self.redis_db.get(name)

        if data is not None and update_expire:  # 保证key存在时设置过期时间
            if not self.redis_db.expire(name, ex):
                aelog.error("set expire failed, name={}".format(name))

        if load_responses:
            with ignore_error():
                data = ujson.loads(data)

        return data

    def is_exist_key(self, name: str) -> bool:
        """
        判断redis key是否存在
        Args:
            name: redis key的名称
        Returns:

        """
        return self.redis_db.exists(name)

    def delete_keys(self, names: List[str]) -> NoReturn:
        """
        删除一个或多个redis key
        Args:
            names: redis key的名称
        Returns:

        """
        names = (names,) if isinstance(names, str) else names
        if not self.redis_db.delete(*names):
            aelog.error("Delete redis keys failed {}.".format(*names))

    def get_keys(self, pattern_name: str) -> List:
        """
        根据正则表达式获取redis的keys
        Args:
            pattern_name:正则表达式的名称
        Returns:

        """
        return self.redis_db.keys(pattern_name)
