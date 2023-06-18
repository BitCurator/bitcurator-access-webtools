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
""" Test database fixture. """
import os
import pytest

from bcaw import APP
from bcaw.database import BASE, ENGINE
from bcaw.model import DB_SESSION, init_db

@pytest.fixture(scope='session')
def app(request):
    """Application test fixture for bcaw Flask app."""
    # Establish an application context before running the tests.
    ctx = APP.app_context()
    ctx.push()

    def teardown():
        """Teardown the test fixture DB."""
        ctx.pop()
        os.unlink(APP.config["SQL_PATH"])

    request.addfinalizer(teardown)
    return APP


@pytest.fixture(scope='session')
def database(application, request):
    """Session-wide test database."""
    def teardown():
        """Drop the test db."""
        BASE.metadata.drop_all(bind=ENGINE)

    BASE.metadata.app = application
    init_db()

    request.addfinalizer(teardown)
    return BASE.metadata


@pytest.fixture(scope='function')
def session(test_db, request):# pylint: disable-msg=W0613
    """Creates a new database session for a test."""
    def teardown():
        """Drop the test db."""
        BASE.metadata.drop_all(bind=ENGINE)
        BASE.commit()

    request.addfinalizer(teardown)
    return DB_SESSION
