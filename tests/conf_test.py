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
