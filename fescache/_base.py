#!/usr/bin/env python3
# coding=utf-8

"""
@author: guoyanfeng
@software: PyCharm
@time: 2020/9/3 下午5:52
"""
import secrets
import uuid
from typing import Any, Dict, Optional, Union

from .utils import ordumps, orloads

__all__ = ("Session", "LONG_EXPIRED", "EXPIRED", "SESSION_EXPIRED", "DAY3_EXPIRED", "DAY7_EXPIRED",
           "DAY15_EXPIRED", "DAY30_EXPIRED", "SHORT_EXPIRED", "BaseStrictRedis")

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

    def __init__(self, account_id: str, *, user_name: str = "", account_type: str = "", user_id: str = "",
                 full_name: str = "", org_id: str = "", org_name: str = "", org_type: str = "",
                 org_level: Optional[int] = None, regiona_no: str = "", gather_orgnos: Optional[Dict[str, str]] = None,
                 department_no: str = "", department_name: str = "", department_type: str = "",
                 department_level: Optional[int] = None, **kwargs):
        # 用户信息
        self.account_id: str = account_id  # 账户ID
        self.user_name: str = user_name
        self.account_type: str = account_type
        self.user_id: str = user_id
        self.full_name: str = full_name
        # 组织信息
        self.org_id: str = org_id
        self.org_name: str = org_name
        self.org_type: str = org_type
        self.org_level: Optional[int] = org_level
        self.regiona_no: str = regiona_no
        self.gather_orgnos: Dict[str, str] = gather_orgnos or {}
        self.department_no: str = department_no
        self.department_name: str = department_name
        self.department_type: str = department_type
        self.department_level: Optional[int] = department_level
        # session信息
        self.session_id: str = secrets.token_urlsafe()  # session ID
        self.role_id: str = uuid.uuid4().hex  # 账户的角色在redis中的ID
        self.menu_id: str = uuid.uuid4().hex  # 账户的页面菜单权限在redis中的ID
        self.data_id: str = uuid.uuid4().hex  # 账户的数据权限在redis中的ID
        self.static_route_id: str = uuid.uuid4().hex  # 账户的静态权限在redis中的ID
        self.dynamic_route_id: str = uuid.uuid4().hex  # 账户的动态权限在redis中的ID
        # 其他信息
        self.kwargs: Dict[str, Any] = {**kwargs}
        for k, v in self.kwargs.items():
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
                 pool_size: int = 25):
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
        self.host: str = host
        self.port: int = port
        self.dbname: int = dbname
        self.passwd: str = passwd
        self.pool_size: int = pool_size

        if app is not None:
            self.init_app(app)
        super().__init__()  # 混入类调用父类初始化方法

    def init_app(self, app, ) -> None:
        """
        redis 非阻塞工具类
        Args:
            app: app应用
        Returns:

        """
        self.app = app
        config: Dict[str, Union[str, int]] = app.config if getattr(app, "config", None) else app.state.config

        self.host = str(config.get("FESCACHE_REDIS_HOST", self.host)) or self.host
        self.port = int(config.get("FESCACHE_REDIS_PORT", self.port)) or self.port
        self.dbname = int(config.get("FESCACHE_REDIS_DBNAME", self.dbname)) or self.dbname
        self.passwd = str(config.get("FESCACHE_REDIS_PASSWD", self.passwd)) or self.passwd
        self.pool_size = int(config.get("FESCACHE_REDIS_POOL_SIZE", self.pool_size)) or self.pool_size

    def init_engine(self, *, host: str = "127.0.0.1", port: int = 6379, dbname: int = 0, passwd: str = "",
                    pool_size: int = 25):
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
        self.passwd = passwd or self.passwd
        self.pool_size = pool_size or self.pool_size

    @staticmethod
    def rs_dumps(hash_data: Dict[str, Any]) -> Dict[str, str]:
        """
        结果dump
        Args:
            hash_data: hash data
        Returns:

        """
        return {hash_key: ordumps(hash_val) if not isinstance(hash_val, str) else hash_val
                for hash_key, hash_val in hash_data.items()}

    @staticmethod
    def rs_loads(hash_data: Dict[str, str]) -> Dict[str, Any]:
        """
        结果load
        Args:
            hash_data: hash data
        Returns:

        """
        return {hash_key: orloads(hash_val) for hash_key, hash_val in hash_data.items()}

    @staticmethod
    def _get_session_keys(session_data: Session):
        """
        获取session中有用的key
        Args:
            session_data: session
        Returns:

        """
        return [session_data.account_id, session_data.session_id, session_data.role_id,
                session_data.menu_id, session_data.data_id, session_data.static_route_id,
                session_data.dynamic_route_id]
