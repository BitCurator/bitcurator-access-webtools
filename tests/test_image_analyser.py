#!/usr/bin/env python
# coding=UTF-8
#
# BitCurator Access Webtools (Disk Image Access for the Web)
# Copyright (C) 2014 - 2023
# All rights reserved.
#
# This code is distributed under the terms of the GNU General Public
# License, Version 3. See the text file "COPYING" for further details
# about the terms of this license.
#
""" Tests for the classes in model.py. """
import os.path
import unittest

from bcaw.image_analyser import GroupFileParser

from .const import THIS_DIR
from .conf_test import database, session, app # pylint: disable-msg=W0611

TEST_ROOT = "__root__"
TEST_GROUP_CONFIG_DIR = os.path.join(THIS_DIR, "group_config")
TEST_GROUP_CONFIG = os.path.join(TEST_GROUP_CONFIG_DIR, "groups.conf")

class GroupFileParserTestCase(unittest.TestCase):
    """ Test cases for the GroupFileParser class and methods. """
    def test_null_config_path(self):
        """ Test case for None name case. """
        parser_test = GroupFileParser()
        with self.assertRaises(ValueError) as _:
            parser_test.parse_config(None)

    def test_group_parse(self): # pylint: disable-msg=R0201
        """Test the parsing of a simple group file."""
        parser_test = GroupFileParser()
        parser_test.parse_config(TEST_GROUP_CONFIG)
        assert len(parser_test.get_groups()) == 3

    def test_path_detect(self): # pylint: disable-msg=R0201
        """Test the parsing of paths from simple group file."""
        parser_test = GroupFileParser()
        parser_test.parse_config(TEST_GROUP_CONFIG)
        for group in parser_test.get_groups():
            assert os.path.exists(os.path.join(THIS_DIR, group['path']))
