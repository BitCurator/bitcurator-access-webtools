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
# model.py holds the database model classes and connection utils
#
"""Database model classes for BitCurator access tools."""
import datetime
import logging
import ntpath
import os

from sqlalchemy import Boolean, BigInteger, Date, DateTime, Integer, String
from sqlalchemy import Column, ForeignKey, ForeignKeyConstraint, func, Table, UniqueConstraint
from sqlalchemy.orm import relationship, backref

from .database import BASE, DB_SESSION, ENGINE
from .const import MimeTypes
from .model_uuid import unique_id
from .utilities import check_param_not_none, sha1_path, identify_mime_path

# Link entity that records image occurence in a group.
GROUP_IMAGES = Table('group_images', BASE.metadata,
                     Column('group_id', Integer, ForeignKey('group.id')),
                     Column('image_id', String(10), ForeignKey('image.id'))
                    )

class Group(BASE):
    """Encapsulation of groups of images. Effectively a root directory, name
    and description."""
    __tablename__ = 'group'
    id = Column(Integer, primary_key=True)
    name = Column(String(256), unique=True)
    description = Column(String(1024))
    images = relationship("Image",
                          secondary=GROUP_IMAGES,
                          backref="groups")

    def __init__(self, name, description):
        self.name = name
        self.description = description

    def add_image(self, image):
        """Add a new image to the group."""
        self.images.append(image)
        DB_SESSION.commit()

    @staticmethod
    def add(group):
        """Add a new group to the database."""
        _add(group)

    @staticmethod
    def count():
        """Find out how many groups are in the DB"""
        return len(Group.query.all())

    @staticmethod
    def all():
        """Get all of the Groups in the DB"""
        return Group.query.order_by(Group.name).all()

    @staticmethod
    def by_id(id_to_get):
        """Get an image by its unique id, returns the image or None if no image
        with that id exists."""
        return Group.query.filter_by(id=id_to_get).first()

    @staticmethod
    def by_name(name):
        """Retrieve all Groups with a particular name."""
        return Group.query.filter_by(name=name).first()

class Image(BASE):
    """ Class that models basic image information that also handles
        convenience methods for instance creation from file system and
        database tables.
    """
    __tablename__ = 'image'
    id = Column(String(10), primary_key=True)
    path = Column(String(4096), unique=True, nullable=False)
    name = Column(String(256))
    added = Column(DateTime(timezone=True), server_default=func.now())
    indexed = Column(DateTime(timezone=True))

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

    def indexed_image(self):
        """
        Update the indexed datetime stamp to indicate that the image has
        been indexed.
        """
        self.indexed = datetime.datetime.utcnow()
        DB_SESSION.commit()

    @staticmethod
    def add(image):
        """Add a new image to the database."""
        if image.id is None:
            image.id = unique_id(Image.by_id)
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

    @staticmethod
    def by_sha1(sha1):
        """Retrieve all Images with a particular sha1."""
        return Image.query.join(ByteSequence).filter_by(sha1=sha1).all()

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
    table = Column(Integer, primary_key=True, autoincrement=False)
    slot = Column(Integer, primary_key=True, autoincrement=False)
    addr = Column(Integer)
    start = Column(Integer)
    description = Column(String(40))

    image_id = Column(String(10), ForeignKey('image.id'), primary_key=True, nullable=False)
    image = relationship('Image', backref=backref('partitions', lazy='dynamic'))

    __table_args__ = (UniqueConstraint('image_id', 'table', 'slot', name='uix_partition_slot'),)

    def __init__(self, image, table, slot, addr=None, start=None, description=None):
        self.image = image
        self.table = table
        self.addr = addr
        self.slot = slot
        self.start = start
        self.description = description

    @staticmethod
    def all():
        """Static method that returns all of the partitions in the table."""
        return Partition.query.order_by(Partition.id).all()

    @staticmethod
    def by_image_table_and_slot(image_id, table, slot):
        """Retrieve a partition by id, returns the partition or None if no partition
        with that id exists."""
        return Partition.query.filter_by(image_id=image_id, table=table, slot=slot).first()

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

    image_id = Column(String(10), nullable=False)
    partition_table = Column(Integer, nullable=False)
    partition_slot = Column(Integer, nullable=False)
    partition = relationship('Partition', backref=backref('file_elements', lazy='dynamic'))

    byte_sequence_id = Column(Integer, ForeignKey('byte_sequence.id'), nullable=False)
    byte_sequence = relationship('ByteSequence', backref=backref('file_elements', lazy='dynamic'))

    __table_args__ = (UniqueConstraint('image_id', 'partition_table', 'partition_slot',
                                       'path', name='uix_partition_path'),
                      ForeignKeyConstraint([image_id, partition_table, partition_slot],
                                           [Partition.image_id, Partition.table, Partition.slot]),
                      {})

    def __init__(self, path, partition, byte_sequence):
        self.path = os.path.abspath(path)
        self.partition = partition
        self.byte_sequence = byte_sequence

    @property
    def name(self):
        """Returns just the name part of the path."""
        return ntpath.basename(self.path)

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
        return FileElement.query.filter_by(image_id=partition.image_id,
                                           partition_slot=partition.slot,
                                           path=path).first()

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
    def in_sha1_set(sha1s):
        """Returns all of the ByteSequences contained in the table whose SHA1s are
        contained in the list of ids."""
        for sha1 in sha1s:
            logging.info("SHA1 found: %s", sha1)
        return ByteSequence.query.filter(ByteSequence.sha1.in_(sha1s)).all()

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
