#!/usr/bin/python
# coding=UTF-8
#
# BitCurator Access Webtools (Disk Image Access for the Web)
# Copyright (C) 2014 - 2016
# All rights reserved.
#
# This code is distributed under the terms of the GNU General Public
# License, Version 3. See the text file "COPYING" for further details
# about the terms of this license.
#
"""Short UUID and SQLAlchemy combined to offer keys for DB tables."""
import shortuuid
from sqlalchemy.types import TypeDecorator, CHAR

shortuuid.set_alphabet("ABCDE0123456789")

class SqlUuid(TypeDecorator): # pylint: disable-msg=W0223
    """Encodes and decodes shortuuid types for SQLAlchemy."""
    impl = CHAR

    def load_dialect_impl(self, dialect):
        return dialect.type_descriptor(CHAR(22))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif not isinstance(value, shortuuid.uuid):
            # hex string
            return shortuuid.encode(shortuuid.uuid(value))
        return shortuuid.encode(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        return shortuuid.uuid(value)

def new_id():
    """Generate a new id that's truncated to 10 characters."""
    full = shortuuid.uuid()
    return full[:10]
