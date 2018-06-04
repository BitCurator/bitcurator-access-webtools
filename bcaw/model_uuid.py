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

shortuuid.set_alphabet("ABCDE0123456789")

def _new_id():
    full = shortuuid.uuid()
    return full[:10]

def unique_id(select_by_id_method):
    """Generate a new unique id that's truncated to 10 characters."""
    id_check = False
    while id_check is False:
        generated_id = _new_id()
        dupe_check = select_by_id_method(generated_id)
        id_check = dupe_check is None
    return generated_id
