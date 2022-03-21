#!/usr/bin/env python
# -*- encoding: utf8 -*-
"""Put All possible exception definition."""


class ArtichokeException(RuntimeError):
    """Base Exception used for every extended exception."""

    def __init__(self, msg):
        """Return message."""
        self.msg = msg
