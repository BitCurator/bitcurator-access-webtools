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
import ntpath
import os

from sqlalchemy import Column, BigInteger, Date, Integer, String, ForeignKey
from sqlalchemy import UniqueConstraint, Boolean
from sqlalchemy.orm import relationship, backref

from .database import BASE, DB_SESSION, ENGINE
from .const import MimeTypes
from .utilities import check_param_not_none, sha1_path, identify_mime_path

class Image(BASE):
    """ Class that models basic image information that also handles
        convenience methods for instance creation from file system and
        database tables.
    """
    __tablename__ = 'image'
    id = Column(Integer, primary_key=True)
    path = Column(String(4096), unique=True)
    name = Column(String(256))

    byte_sequence_id = Column(Integer, ForeignKey('byte_sequence.id'), nullable=False)
    byte_sequence = relationship('ByteSequence', backref=backref('images', lazy='dynamic'))

    image_details_id = Column(Integer, ForeignKey('image_details.id'))
    details = relationship('ImageDetails', backref=backref('image', lazy='dynamic'))

    image_properties_id = Column(Integer, ForeignKey('image_properties.id'), nullable=False)
    properties = relationship('ImageProperties', backref=backref('image', lazy='dynamic'))

    def __init__(self, path, byte_sequence, details=None, properties=None):
        self.path = path
        self.name = ntpath.basename(path)
        self.byte_sequence = byte_sequence
        self.details = details
        self.properties = properties

    def get_partitions(self):
        """Returns all of the image's partitions."""
        return self.partitions.all()

    @staticmethod
    def add(image):
        """Add a new image to the database."""
        _add(image)

    @staticmethod
    def count():
        """Find out how many images are in the DB"""
        return len(Image.query.all())

    @staticmethod
    def all():
        """Get all of the images in the DB"""
        return Image.query.order_by(Image.path).all()

    @staticmethod
    def by_id(id_to_get):
        """Get an image by its unique id, returns the image or None if no image
        with that id exists."""
        return Image.query.filter_by(id=id_to_get).first()

    @staticmethod
    def by_path(path):
        """Retrieve a particular image by path."""
        return Image.query.filter_by(path=path).first()

class ImageDetails(BASE):
    """Models the image details metadata."""
    __tablename__ = 'image_details'
    id = Column(Integer, primary_key=True)
    acquired = Column(Date)
    system_date = Column(Date)
    operating_system = Column(String(256))
    format = Column(String(30))
    media_type = Column(String(30))
    is_physical = Column(Boolean)
    md5 = Column(String(50))

    def __init__(self, acquired=None, system_date=None, operating_system=None,
                 image_format=None, media_type=None, is_physical=None, md5=None):
        self.acquired = acquired
        self.system_date = system_date
        self.operating_system = operating_system
        self.format = image_format
        self.media_type = media_type
        self.is_physical = is_physical
        self.md5 = md5

    @staticmethod
    def add(details):
        """Add a new ImageDetails to the database."""
        _add(details)

    @staticmethod
    def count():
        """Find out how many ImageDetails are in the DB"""
        return len(ImageDetails.query.all())

    @staticmethod
    def all():
        """Get all of the ImageDetails in the DB"""
        return ImageDetails.query.order_by(ImageDetails.name).all()

    @staticmethod
    def by_id(id_to_get):
        """Get ImageDetails by unique id, returns the ImageDetails or None if no details
        with that id exists."""
        return ImageDetails.query.filter_by(id=id_to_get).first()

class ImageProperties(BASE):
    """Physical properties of an image."""
    __tablename__ = 'image_properties'
    id = Column(Integer, primary_key=True)
    bps = Column(Integer)
    sectors = Column(Integer)
    size = Column(BigInteger)

    def __init__(self, bps=None, sectors=None, size=None):
        self.bps = bps
        self.sectors = sectors
        self.size = size

    @staticmethod
    def add(properties):
        """Add a new ImageProperties to the database."""
        _add(properties)

    @staticmethod
    def count():
        """Find out how many ImageProperties are in the DB"""
        return len(ImageProperties.query.all())

    @staticmethod
    def all():
        """Get all of the ImageProperties in the DB"""
        return ImageProperties.query.order_by(ImageProperties.size).all()

    @staticmethod
    def by_id(id_to_get):
        """Get ImageProperties by unique id, returns the ImageProperties or None
        if no properies with that id exists."""
        return ImageProperties.query.filter_by(id=id_to_get).first()

class Partition(BASE):
    """Models a partition from a disk image."""
    __tablename__ = 'partition'
    id = Column(Integer, primary_key=True)
    addr = Column(Integer)
    slot = Column(Integer)
    start = Column(Integer)
    description = Column(String(40))

    image_id = Column(Integer, ForeignKey('image.id'), nullable=False)
    image = relationship('Image', backref=backref('partitions', lazy='dynamic'))

    def __init__(self, image, addr=None, slot=None, start=None, description=None):
        self.image = image
        self.addr = addr
        self.slot = slot
        self.start = start
        self.description = description

    @staticmethod
    def all():
        """Static method that returns all of the partitions in the table."""
        return Partition.query.order_by(Partition.id).all()

    @staticmethod
    def by_id(id_to_get):
        """Retrieve a partition by id, returns the partition or None if no partition
        with that id exists."""
        return Partition.query.filter_by(id=id_to_get).first()

    @staticmethod
    def add(part):
        """Add a new partition to the datatbase."""
        _add(part)

class FileElement(BASE):
    """
    Class to hold basic details of a ByteSequence, used in file analysis.
    """
    __tablename__ = 'file_element'
    id = Column(Integer, primary_key=True)# pylint: disable-msg=C0103
    path = Column(String(4096), nullable=False)

    partition_id = Column(Integer, ForeignKey('partition.id'), nullable=False)
    partition = relationship('Partition', backref=backref('file_elements', lazy='dynamic'))

    byte_sequence_id = Column(Integer, ForeignKey('byte_sequence.id'), nullable=False)
    byte_sequence = relationship('ByteSequence', backref=backref('file_elements', lazy='dynamic'))

    __table_args__ = (UniqueConstraint('partition_id', 'path', name='uix_partition_path'),)

    def __init__(self, path, partition, byte_sequence):
        self.path = path
        self.partition = partition
        self.byte_sequence = byte_sequence

    @staticmethod
    def count():
        """Find out how many FileElements are in the DB"""
        return len(FileElement.query.all())

    @staticmethod
    def all():
        """Static method that returns all of the FileElements in the table."""
        return FileElement.query.order_by(FileElement.id).all()

    @staticmethod
    def by_id(id_to_get):
        """Retrieve a file element by id, returns the element or None if no element
        with that id exists."""
        return FileElement.query.filter_by(id=id_to_get).first()

    @staticmethod
    def by_partition_and_path(partition, path):
        """Retrieve a file element by partition and path."""
        return FileElement.query.filter_by(partition_id=partition.id, path=path).first()

    @staticmethod
    def add(element):
        """Add a new FileElement to the datatbase."""
        _add(element)

class ByteSequence(BASE):
    """
    Class to hold basic details of a ByteSequence, used in file analysis.
    """
    __tablename__ = 'byte_sequence'
    id = Column(Integer, primary_key=True)# pylint: disable-msg=C0103
    sha1 = Column(String(40), unique=True, nullable=False)
    size = Column(BigInteger, nullable=False)
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
    def count():
        """Find out how many ByteSequence are in the DB"""
        return len(ByteSequence.query.all())

    @staticmethod
    def all():
        """Static method that returns all of the ByteSequence in the table."""
        return ByteSequence.query.order_by(ByteSequence.id).all()

    @staticmethod
    def by_id(id_to_get):
        """Retrieve a byte sequence by id, returns the sequence or None if no sequence
        with that id exists."""
        return ByteSequence.query.filter_by(id=id_to_get).first()

    @staticmethod
    def by_sha1(sha1_to_get):
        """Retrieve a byte sequence by sha1, returns the sequence or None if no sequence
        with that sha1 exists."""
        return ByteSequence.query.filter_by(sha1=sha1_to_get).first()

    @staticmethod
    def from_path(path):
        """Create a new ByteSequence from a given path."""
        sha1 = sha1_path(path)
        byte_sequence = ByteSequence.by_sha1(sha1)

        if byte_sequence is not None:
            return byte_sequence

        mime_type = identify_mime_path(path)
        size = os.stat(path).st_size
        return ByteSequence(sha1, size, mime_type)

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
