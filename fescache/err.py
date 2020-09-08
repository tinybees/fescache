#!/usr/bin/env python3
# coding=utf-8

"""
@author: guoyanfeng
@software: PyCharm
@time: 18-12-25 下午2:08
"""

__all__ = ("Error", "RedisClientError", "RedisConnectError", "FuncArgsError", "RedisTimeoutError")


class Error(Exception):
    """
    异常基类
    """

    def __init__(self, message=None):
        self.message = message

    def __str__(self):
        return "Error: message='{}'".format(self.message)

    def __repr__(self):
        return "<{} '{}'>".format(self.__class__.__name__, self.message)


class RedisClientError(Error):
    """
    主要处理redis的error
    """

    pass


class RedisConnectError(RedisClientError):
    """
    主要处理redis的connect error
    """
    pass


class RedisTimeoutError(RedisClientError):
    """
    主要处理redis的connect error
    """
    pass


class FuncArgsError(Error):
    """
    处理函数参数不匹配引发的error
    """

    pass
