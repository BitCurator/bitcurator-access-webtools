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
# This file contains items that can be configured in BitCurator Access Webtools.
#
import os
from flask import Flask

# TODO: template these values for flexible install
HOST = 'localhost'
DB_HOST = 'localhost'
ROOT = '/var/www/bcaw/'
LOG_ROOT = '/var/log/'
DB_USER = 'vagrant'
DB_PASS = 'vagrant'
DB_NAME = 'bca_db'
POSTGRES_URI = 'postgresql://' + DB_USER + ':' + DB_PASS + '@' + DB_HOST + '/' + DB_NAME

class BaseConfig(object):
    HOST = HOST
    IMAGE_DIR = ROOT + 'disk-images'
    SQLALCHEMY_DATABASE_URI = POSTGRES_URI
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DEBUG = False
    LOG_FORMAT = '[%(filename)-15s:%(lineno)-5d] %(message)s'
    LOG_FILE = LOG_ROOT + 'bcaw.log'

class DevConfig(BaseConfig):
    DEBUG = True
    LOG_FORMAT = '[%(levelname)-8s %(filename)-15s:%(lineno)-5d %(funcName)-30s] %(message)s'

CONFIGS = {
    "dev": 'bcaw.config.DevConfig',
    "default": 'bcaw.config.BaseConfig'
}

def configure_app(app):
    config_name = os.getenv('BCAW_CONFIG', 'dev');
    app.config.from_object(CONFIGS[config_name])
