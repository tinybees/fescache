#!/usr/bin/env python3
# coding=utf-8

"""
@author: guoyanfeng
@software: PyCharm
@time: 2020/9/3 下午5:52
"""
import secrets
import uuid

__all__ = ("Session", "LONG_EXPIRED", "EXPIRED", "SESSION_EXPIRED", "DAY3_EXPIRED", "DAY7_EXPIRED",
           "DAY15_EXPIRED", "DAY30_EXPIRED", "SHORT_EXPIRED", "BaseStrictRedis")

from typing import Dict, Any

import ujson

from fescache import ignore_error

SESSION_EXPIRED: int = 30 * 60  # session过期时间
SHORT_EXPIRED: int = 60 * 60  # 短session过期时间
EXPIRED: int = 12 * 60 * 60  # 通用过期时间
LONG_EXPIRED: int = 24 * 60 * 60  # 最长过期时间
DAY3_EXPIRED: int = 3 * LONG_EXPIRED
DAY7_EXPIRED: int = 7 * LONG_EXPIRED
DAY15_EXPIRED: int = 15 * LONG_EXPIRED
DAY30_EXPIRED: int = 30 * LONG_EXPIRED


class Session(object):
    """
    保存实际看结果的session实例
    Args:

    """

    def __init__(self, account_id: str, *,
                 session_id: str = None,
                 org_id: str = None,
                 role_id: str = None,
                 menu_id: str = None,
                 static_route_id: str = None,
                 dynamic_route_id: str = None,
                 **kwargs):
        self.account_id = account_id  # 账户ID
        self.session_id = secrets.token_urlsafe() if not session_id else session_id  # session ID
        self.org_id = org_id or uuid.uuid4().hex  # 账户的组织结构在redis中的ID
        self.role_id = role_id or uuid.uuid4().hex  # 账户的角色在redis中的ID
        self.menu_id = menu_id or uuid.uuid4().hex  # 账户的页面菜单权限在redis中的ID
        self.static_route_id = static_route_id or uuid.uuid4().hex  # 账户的静态权限在redis中的ID
        self.dynamic_route_id = dynamic_route_id or uuid.uuid4().hex  # 账户的动态权限在redis中的ID
        for k, v in kwargs.items():
            setattr(self, k, v)

    def to_dict(self, ) -> Dict:
        """

        Args:

        Returns:

        """
        return dict(vars(self))


class BaseStrictRedis(object):
    """
    redis 基类
    """

    def __init__(self, app=None, *, host: str = "127.0.0.1", port: int = 6379, dbname: int = 0, passwd: str = "",
                 pool_size: int = 50):
        """
        redis 基类
        Args:
            app: app应用
            host:redis host
            port:redis port
            dbname: database name
            passwd: redis password
            pool_size: redis pool size
        """
        self.app = app
        self.host = host
        self.port = port
        self.dbname = dbname
        self.passwd = passwd
        self.pool_size = pool_size

        if app is not None:
            self.init_app(app, host=self.host, port=self.port, dbname=self.dbname, passwd=self.passwd,
                          pool_size=self.pool_size)

    def init_app(self, app, *, host: str = None, port: int = None, dbname: int = None, passwd: str = "",
                 pool_size: int = None):
        """
        redis 非阻塞工具类
        Args:
            app: app应用
            host:redis host
            port:redis port
            dbname: database name
            passwd: redis password
            pool_size: redis pool size
        Returns:

        """
        self.app = app

        self.host = host or app.config.get("FESCACHE_REDIS_HOST", None) or self.host
        self.port = port or app.config.get("FESCACHE_REDIS_PORT", None) or self.port
        self.dbname = dbname or app.config.get("FESCACHE_REDIS_DBNAME", None) or self.dbname
        passwd = passwd or app.config.get("FESCACHE_REDIS_PASSWD", None) or self.passwd
        self.pool_size = pool_size or app.config.get("FESCACHE_REDIS_POOL_SIZE", None) or self.pool_size
        self.passwd = passwd if passwd is None else str(passwd)

    def init_engine(self, *, host: str = None, port: int = None, dbname: int = None, passwd: str = "",
                    pool_size: int = None):
        """
        redis 非阻塞工具类
        Args:
            host:redis host
            port:redis port
            dbname: database name
            passwd: redis password
            pool_size: redis pool size
        Returns:

        """
        self.host = host or self.host
        self.port = port or self.port
        self.dbname = dbname or self.dbname
        passwd = passwd or self.passwd
        self.pool_size = pool_size or self.pool_size

        self.passwd = passwd if passwd is None else str(passwd)

    @staticmethod
    def response_dumps(is_dump: bool, hash_data: Dict) -> Dict[str, Any]:
        """
        结果dump
        Args:
            is_dump: 是否dump
            hash_data: hash data
        Returns:

        """
        # 是否对每个键值进行dump
        if is_dump:
            hash_data_ = {}
            for hash_key, hash_val in hash_data.items():
                if not isinstance(hash_val, str):
                    with ignore_error():
                        hash_val = ujson.dumps(hash_val)
                hash_data_[hash_key] = hash_val
            hash_data = hash_data_

        return hash_data

    @staticmethod
    def responses_loads(is_load: bool, hash_data: Dict):
        """
        结果load
        Args:
            is_load: 是否load
            hash_data: hash data
        Returns:

        """
        if is_load:
            hash_data_ = {}
            for hash_key, hash_val in hash_data.items():
                with ignore_error():
                    hash_val = ujson.loads(hash_val)
                hash_data_[hash_key] = hash_val
            hash_data = hash_data_

        return hash_data

    @staticmethod
    def _get_session_keys(session_data: Session):
        """
        获取session中有用的key
        Args:
            session_data: session
        Returns:

        """
        return [session_data.session_id, session_data.account_id, session_data.org_id, session_data.role_id,
                session_data.permission_id, session_data.static_permission_id, session_data.dynamic_permission_id,
                session_data.page_id, session_data.page_menu_id]
