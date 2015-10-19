#!/usr/bin/python
# coding=UTF-8
#
# BitCurator Access Webtools (Disk Image Access for the Web)
# Copyright (C) 2014
# All rights reserved.
#
# This code is distributed under the terms of the GNU General Public
# License, Version 3. See the text file "COPYING" for further details
# about the terms of this license.
#
# This file contains items that can be configured in BitCurator Access Webtools.
#
# IMAGEDIR - the local directory containing your disk images
# SQLALCHEMY_DATABASE_URI - the local db URI (you must configure a postgres
#                           database before running the main script.

IMAGEDIR = "/vagrant/disk-images"
#SQLALCHEMY_DATABASE_URI = "postgresql://bcadmin:bcadmin@localhost/bcdb"
SQLALCHEMY_DATABASE_URI = "postgresql://vagrant:vagrant@localhost/bca_db"
INDEX_DIR = "/vagrant/lucene_index"
FILES_TO_INDEX_DIR = "/vagrant/files_to_index"
