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
from sqlalchemy import Column, BigInteger, Date, Integer, String, ForeignKey
from sqlalchemy import UniqueConstraint, Boolean
from sqlalchemy.orm import relationship, backref

from .database import BASE, DB_SESSION, ENGINE
from .const import MimeTypes
from .utilities import check_param_not_none

class Image(BASE):
    """ Class that models basic image information that also handles
        convenience methods for instance creation from file system and
        database tables.
    """
    __tablename__ = 'image'
    id = Column(Integer, primary_key=True)
    path = Column(String(512), unique=True)
    name = Column(String(256))
    acquired = Column(Date)
    system_date = Column(Date)
    os = Column(String(256))
    format = Column(String(30))
    media_type = Column(String(30))
    is_physical = Column(Boolean)
    bps = Column(Integer)
    sectors = Column(Integer)
    size = Column(BigInteger)
    md5 = Column(String(50))

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
        """Find out how many images are in the """
        return len(Image.query.all())

    @staticmethod
    def images():
        """Get all of the images in the """
        return Image.query.order_by(Image.path).all()

    @staticmethod
    def by_path(path):
        """Retrieve a particular image by path."""
        return Image.query.filter_by(path=path).first()

    @staticmethod
    def by_id(id_to_get):
        """Get an image by its unique id, returns the image or None if no image
        with that id exists."""
        return Image.query.filter_by(id=id_to_get).first()

    @staticmethod
    def add_image(image):
        """Add a new image to the database."""
        _add(image)

class Partition(BASE):
    """Models a partition from a disk image."""
    __tablename__ = 'partition'
    id = Column(Integer, primary_key=True)
    addr = Column(Integer)
    slot = Column(Integer)
    start = Column(Integer)
    description = Column(String(40))

    image_id = Column(Integer, ForeignKey('image.id'))
    image = relationship('Image', backref=backref('partitions', lazy='dynamic'))

    def __init__(self, addr=None, slot=None, start=None, description=None, image_id=None):
        self._addr = addr
        self.slot = slot
        self.start = start
        self.description = description
        self.image_id = image_id

    @staticmethod
    def partitions():
        """Static method that returns all of the partitions in the table."""
        return Partition.query.order_by(Partition.id).all()

    @staticmethod
    def by_id(id_to_get):
        """Retrieve a partition by id, returns the partition or None if no partition
        with that id exists."""
        return Partition.query.filter_by(id=id_to_get).first()

    @staticmethod
    def add_part(part):
        """Add a new partition to the datatbase."""
        _add(part)

class FileElement(BASE):
    """
    Class to hold basic details of a ByteSequence, used in file analysis.
    """
    __tablename__ = 'file_element'
    id = Column(Integer, primary_key=True)# pylint: disable-msg=C0103
    path = Column(String(4096), nullable=False)

    partition_id = Column(Integer, ForeignKey('partition.id'))
    partition = relationship('Partition', backref=backref('file_elements', lazy='dynamic'))

    __table_args__ = (UniqueConstraint('partition_id', 'path', name='uix_partition_path'),)

    @staticmethod
    def file_elements():
        """Static method that returns all of the FileElements in the table."""
        return FileElement.query.order_by(FileElement.id).all()

    @staticmethod
    def by_id(id_to_get):
        """Retrieve a file element by id, returns the element or None if no element
        with that id exists."""
        return FileElement.query.filter_by(id=id_to_get).first()

    @staticmethod
    def add_element(element):
        """Add a new FileElement to the datatbase."""
        _add(element)

class ByteSequence(BASE):
    """
    Class to hold basic details of a ByteSequence, used in file analysis.
    """
    __tablename__ = 'byte_sequence'
    id = Column(Integer, primary_key=True)# pylint: disable-msg=C0103
    sha1 = Column(String(40), unique=True, nullable=False)
    size = Column(Integer, nullable=False)
    mime_type = Column(String(255))

    EMPTY_SHA1 = 'da39a3ee5e6b4b0d3255bfef95601890afd80709'

    def __init__(self, sha1=EMPTY_SHA1, size=0, mime_type=MimeTypes.BINARY):
        if size < 0:
            raise ValueError("Argument size can not be less than zero.")
        if size < 1 and sha1 != self.EMPTY_SHA1:
            raise ValueError('If size is zero SHA1 must be {}'.format(self.EMPTY_SHA1))
        self.sha1 = sha1
        self.size = size
        self.mime_type = mime_type

    @staticmethod
    def byte_sequences():
        """Static method that returns all of the FileElements in the table."""
        return ByteSequence.query.order_by(ByteSequence.id).all()

    @staticmethod
    def by_id(id_to_get):
        """Retrieve a byte sequence by id, returns the sequence or None if no sequence
        with that id exists."""
        return ByteSequence.query.filter_by(id=id_to_get).first()

    @staticmethod
    def add_byte_sequence(sequence):
        """Add a new ByteSequence to the datatbase."""
        _add(sequence)


def init_db():
    """Initialise the database."""
    BASE.metadata.create_all(bind=ENGINE)

def _add(obj):
    """Add an object instance to the database."""
    check_param_not_none(obj, "obj")
    DB_SESSION.add(obj)
    DB_SESSION.commit()

def _add_all(objects):
    """Add all objects form an iterable to the database."""
    check_param_not_none(objects, "objects")
    for obj in objects:
        check_param_not_none(obj, "obj")
        DB_SESSION.add(obj)
    DB_SESSION.commit()
