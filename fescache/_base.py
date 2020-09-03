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
           "DAY15_EXPIRED", "DAY30_EXPIRED")

SESSION_EXPIRED: int = 30 * 60  # session过期时间
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

    def __init__(self, account_id: str, *, session_id: str = None, org_id: str = None, role_id: str = None,
                 permission_id: str = None, **kwargs):
        self.account_id = account_id  # 账户ID
        self.session_id = secrets.token_urlsafe() if not session_id else session_id  # session ID
        self.org_id = org_id or uuid.uuid4().hex  # 账户的组织结构在redis中的ID
        self.role_id = role_id or uuid.uuid4().hex  # 账户的角色在redis中的ID
        self.permission_id = permission_id or uuid.uuid4().hex  # 账户的权限在redis中的ID
        self.static_permission_id = uuid.uuid4().hex  # 账户的静态权限在redis中的ID
        self.dynamic_permission_id = uuid.uuid4().hex  # 账户的动态权限在redis中的ID
        self.page_id = uuid.uuid4().hex  # 账户的页面权限在redis中的ID
        self.page_menu_id = uuid.uuid4().hex  # 账户的页面菜单权限在redis中的ID
        for k, v in kwargs.items():
            setattr(self, k, v)
