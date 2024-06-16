#!/usr/bin/env python3
# coding=utf-8

"""
@author: guoyanfeng
@software: PyCharm
@time: 18-12-26 下午3:32
"""
from contextlib import contextmanager
from typing import Any, Generator, Union

import orjson

__all__ = ("ignore_error", "ordumps", "orloads")


@contextmanager
def ignore_error(error=Exception) -> Generator[None, None, None]:
    """
    个别情况下会忽略遇到的错误
    Args:

    Returns:

    """
    # noinspection PyBroadException
    try:
        yield
    except error:
        pass


def ordumps(any_value: Any) -> str:
    """

    Args:

    Returns:

    """
    # noinspection PyBroadException
    try:
        return orjson.dumps(any_value).decode()
    except Exception:
        return str(any_value)


def orloads(any_value: Union[bytes, bytearray, memoryview, str]) -> Any:
    """

    Args:

    Returns:

    """
    # noinspection PyBroadException
    try:
        return orjson.loads(any_value)
    except Exception:
        return str(any_value)
