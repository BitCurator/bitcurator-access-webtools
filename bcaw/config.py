#!/usr/bin/python
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
# This file contains items that can be configured in BitCurator Access Webtools.
#
import logging
import os
import tempfile

from .const import ENV_CONF_PROFILE, ENV_CONF_FILE

# TODO: template these values
HOST = 'localhost'
DB_HOST = 'localhost'
ROOT = '/var/www/bcaw/'
LOG_ROOT = '/var/log/'
DB_USER = 'vagrant'
DB_PASS = 'vagrant'
DB_NAME = 'bca_db'
POSTGRES_URI = 'postgresql://' + DB_USER + ':' + DB_PASS + '@' + DB_HOST + '/' + DB_NAME
LUCENE_ROOT = '/var/www/.index'
TEMP = tempfile.gettempdir()

class BaseConfig(object):# pylint: disable-msg=R0903
    """The default configuration."""
    HOST = HOST
    SQLALCHEMY_DATABASE_URI = POSTGRES_URI
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DEBUG = False
    LOG_FORMAT = '[%(asctime)-15s %(filename)-15s:%(lineno)-5d] %(message)s'
    LOG_FILE = LOG_ROOT + 'bcaw.log'
    LOG_LEVEL = logging.INFO
    LUCENE_INDEX_DIR = LUCENE_ROOT
    GROUPS = [
        {
            'name' : 'Test Images',
            'path' : '/var/bcaw/disk-images',
            'description' : 'The set of test disk images supplied with BitCurator.'
        }
    ]

class DevConfig(BaseConfig):# pylint: disable-msg=R0903
    """Development config extras."""
    NAME = 'Development'
    DEBUG = True
    LOG_LEVEL = logging.DEBUG
    LOG_FORMAT = '[%(asctime)-15s %(levelname)-8s %(filename)-15s:'+\
                 '%(lineno)-5d %(funcName)-30s] %(message)s'

class TestConfig(DevConfig):# pylint: disable-msg=R0903
    """Developer level config, with debug logging and long log format."""
    NAME = 'Testing'
    SQL_PATH = os.path.join(TEMP, 'test.db')
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + SQL_PATH
    LOG_FILE = os.path.join(TEMP, 'bcaw.log')

class AnalyserConfig(BaseConfig):# pylint: disable-msg=R0903
    """Configure Image analysis logging."""
    NAME = "Analyser"
    LOG_FORMAT = '[%(asctime)-15s %(levelname)-8s %(filename)-15s:'+\
                 '%(lineno)-5d %(funcName)-30s] %(message)s'
    LOG_FILE = LOG_ROOT + 'bcaw-analyser.log'

CONFIGS = {
    "default": 'bcaw.config.BaseConfig',
    "dev": 'bcaw.config.DevConfig',
    "test": 'bcaw.config.TestConfig',
    "analyser": 'bcaw.config.AnalyserConfig'
}

def configure_app(app):
    """Configure the application using the config env var."""
    config_name = os.getenv(ENV_CONF_PROFILE, 'dev')
    app.config.from_object(CONFIGS[config_name])
    if os.getenv(ENV_CONF_FILE):
        app.config.from_envvar(ENV_CONF_FILE)
