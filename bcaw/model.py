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
# model.py holds the database model classes and connection utils
#
"""Database model classes for BitCurator access tools."""
import logging
from flask_sqlalchemy import SQLAlchemy
from bcaw import app
from bcaw.const import MimeTypes

DATABASE = SQLAlchemy(app)

class Image(DATABASE.Model):
    """ Class that models basic image information that also handles
        convenience methods for instance creation from file system and
        database tables.
    """
    __tablename__ = 'image'
    id = DATABASE.Column(DATABASE.Integer, primary_key=True)
    path = DATABASE.Column(DATABASE.String(512), unique=True)
    name = DATABASE.Column(DATABASE.String(256))
    acquired = DATABASE.Column(DATABASE.Date)
    system_date = DATABASE.Column(DATABASE.Date)
    os = DATABASE.Column(DATABASE.String(256))
    format = DATABASE.Column(DATABASE.String(30))
    media_type = DATABASE.Column(DATABASE.String(30))
    is_physical = DATABASE.Column(DATABASE.Boolean)
    bps = DATABASE.Column(DATABASE.Integer)
    sectors = DATABASE.Column(DATABASE.Integer)
    size = DATABASE.Column(DATABASE.BigInteger)
    md5 = DATABASE.Column(DATABASE.String(50))

    def __init__(self, path, name, acquired=None, system_date=None, os=None,
                 format=None, media_type=None, is_physical=None, bps=None,
                 sectors=None, size=None, md5=None):
        self.path = path
        self.name = name
        self.acquired = acquired
        self.system_date = system_date
        self.os = os
        self.format = format
        self.media_type = media_type
        self.is_physical = is_physical
        self.bps = bps
        self.sectors = sectors
        self.size = size
        self.md5 = md5

    def get_partitions(self):
        """Returns all of the image's partitions."""
        return self.partitions.all()

    @staticmethod
    def image_count():
        """Find out how many images are in the database."""
        return len(Image.query.all())

    @staticmethod
    def images():
        """Get all of the images in the database."""
        return Image.query.order_by(Image.path).all()

    @staticmethod
    def by_path(path):
        """Retrieve a particular image by path."""
        return Image.query.filter_by(path=path).first()

    @staticmethod
    def by_id(id):
        """Get an image by its unique id."""
        return Image.query.filter_by(id=id).first_or_404()

    @staticmethod
    def addImage(image):
        """Add a new image to the database."""
        DATABASE.session.add(image)
        DATABASE.session.commit()

class Partition(DATABASE.Model):
    """Models a partition from a disk image."""
    __tablename__ = 'partition'
    id = DATABASE.Column(DATABASE.Integer, primary_key=True)
    addr = DATABASE.Column(DATABASE.Integer)
    slot = DATABASE.Column(DATABASE.Integer)
    start = DATABASE.Column(DATABASE.Integer)
    description = DATABASE.Column(DATABASE.String(40))

    image_id = DATABASE.Column(DATABASE.Integer, DATABASE.ForeignKey('image.id'))
    image = DATABASE.relationship('Image', backref=DATABASE.backref('partitions', lazy='dynamic'))

    def __init__(self, addr=None, slot=None, start=None, description=None, image_id=None):
        self._addr = addr
        self.slot = slot
        self.start = start
        self.description = description
        self.image_id = image_id

    @staticmethod
    def partitions():
        """Static method that returns all of the partitions in the table."""
        return Image.query.order_by(Partition.id).all()

    @staticmethod
    def by_id(id):
        """Retrieve a partition by id."""
        return Partition.query.filter_by(id=id).first_or_404()

    @staticmethod
    def addPart(part):
        """Add a new partition to the database."""
        DATABASE.session.add(part)
        DATABASE.session.commit()

class ByteSequence(object):
    """
    Class to hold basic details of a ByteSequence, used in file analysis.
    """
    __tablename__ = 'byte_sequence'
    id = DATABASE.Column(DATABASE.Integer, primary_key=True)# pylint: disable-msg=C0103
    sha1 = DATABASE.Column(DATABASE.String(40), unique=True, nullable=False)
    size = DATABASE.Column(DATABASE.Integer, nullable=False)
    mime_type = DATABASE.Column(DATABASE.String(255))

    EMPTY_SHA1 = 'da39a3ee5e6b4b0d3255bfef95601890afd80709'

    def __init__(self, sha1=EMPTY_SHA1, size=0, mime_type=MimeTypes.BINARY):
        if size < 0:
            raise ValueError("Argument size can not be less than zero.")
        if size < 1 and sha1 != self.EMPTY_SHA1:
            raise ValueError('If size is zero SHA1 must be {}'.format(self.EMPTY_SHA1))
        self.sha1 = sha1
        self.size = size
        self.mime_type = mime_type

def dbinit():
    """Initialise the application database, including creating tables if necessary."""
    DATABASE.create_all()
    logging.debug("Database initialised")
