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
import logging
from flask_sqlalchemy import SQLAlchemy
from bcaw import app

db = SQLAlchemy(app)

class Image(db.Model):
    """ Class that models basic image information that also handles
        convenience methods for instance creation from file system and
        database tables.
    """
    __tablename__ = 'image'
    id = db.Column(db.Integer, primary_key=True)
    path = db.Column(db.String(512), unique=True)
    name = db.Column(db.String(256))
    acquired = db.Column(db.Date)
    system_date = db.Column(db.Date)
    os = db.Column(db.String(256))
    format = db.Column(db.String(30))
    media_type = db.Column(db.String(30))
    is_physical = db.Column(db.Boolean)
    bps = db.Column(db.Integer)
    sectors = db.Column(db.Integer)
    size = db.Column(db.BigInteger)
    md5 = db.Column(db.String(50))

    def __init__(self, path, name, acquired = None, system_date = None, os = None, format = None, media_type = None, is_physical = None, bps = None, sectors = None, size = None, md5 = None):
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

    def getPartitions(self):
        return self.partitions.all()

    @staticmethod
    def imageCount():
        return len(Image.query.all())

    @staticmethod
    def images():
        return Image.query.order_by(Image.path).all()

    @staticmethod
    def byPath(path):
        return Image.query.filter_by(path=path).first()

    @staticmethod
    def byId(id):
        return Image.query.filter_by(id=id).first_or_404()

    @staticmethod
    def addImage(image):
        db.session.add(image)
        db.session.commit()

class Partition(db.Model):
    __tablename__ = 'partition'
    id = db.Column(db.Integer, primary_key=True)
    addr = db.Column(db.Integer)
    slot = db.Column(db.Integer)
    start = db.Column(db.Integer)
    description = db.Column(db.String(40))

    image_id = db.Column(db.Integer, db.ForeignKey('image.id'))
    image = db.relationship('Image', backref=db.backref('partitions', lazy='dynamic'))

    def __init__(self, addr=None, slot=None, start=None, description=None, image_id=None):
        self._addr = addr
        self.slot = slot
        self.start = start
        self.description = description
        self.image_id = image_id

    @staticmethod
    def partitions():
        return Image.query.order_by(Partition.id).all()

    @staticmethod
    def byId(id):
        return Partition.query.filter_by(id=id).first_or_404()

    @staticmethod
    def addPart(part):
        db.session.add(part)
        db.session.commit()

def dbinit():
    db.create_all()
    logging.debug("Database initialised")
