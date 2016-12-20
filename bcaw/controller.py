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

import os, ntpath, urllib
from flask import Flask, render_template, send_from_directory, Response, stream_with_context
from bcaw import app
from bcaw.const import ConfKey
from bcaw.disk_utils import ImageDir, ImageFile, FileSysEle
from bcaw.model import *

# Keep a list of images
IMAGE_DIR = ImageDir.fromRootDir(app.config[ConfKey.IMAGE_DIR])

@app.route('/')
def bcaw_home():
    # If there's a different number of images on disk than
    # in the DB table it's time to synch
    if DbSynch.is_synch_db():
        DbSynch.synch_db()

    return render_template('home.html', db_images=Image.images())

@app.route('/image/meta/<id>/')
def image_meta(id):
    image = Image.byId(id)
    return render_template('image.html', image=image)

@app.route('/image/data/<id>/')
def image_dnld(id):
    image = Image.byId(id)
    parent = os.path.abspath(os.path.join(image.path, os.pardir))
    return send_from_directory(parent, image.name, as_attachment=True)

@app.route('/image/<id>/')
def image_parts(id):
    image = Image.byId(id)
    logging.debug("Getting parts for image: " + image.name)
    for part in image.partitions.all():
        logging.debug("Part " + str(part.id))
    return render_template('partitions.html', image=image, partitions=image.getPartitions())

@app.route('/image/<image_id>/<part_id>/')
def part_root(image_id, part_id):
    return file_handler(image_id, part_id, "/")

@app.route('/image/<image_id>/<part_id>/', defaults={'encoded_filepath': '/'})
@app.route('/image/<image_id>/<part_id>/<path:encoded_filepath>/')
def file_handler(image_id, part_id, encoded_filepath):
    file_path = urllib.unquote(encoded_filepath)
    image = Image.byId(image_id)
    imagePart = Partition.byId(part_id)
    fsEle = FileSysEle.fromImagePath(image.path, imagePart, image.bps, file_path)
    if fsEle.isDirectory():
        # Render the dir listing template
        files = FileSysEle.listFiles(image.path, imagePart, image.bps, file_path)
        return render_template('directory.html', image=image, partition=imagePart, files=files)
    # Its a file so return the download
    generator, mime_type = FileSysEle.getPayload(image.path, imagePart.start, image.bps, fsEle)
    return Response(stream_with_context(generator),
                    mimetype=mime_type,
                    headers={ "Content-Disposition" : "attachment;filename=" + fsEle.name })

@app.route('/analysis/<image_id>/<part_id>/<path:encoded_filepath>')
def analysis_handler(image_id, part_id, encoded_filepath):
    file_path = urllib.unquote(encoded_filepath)
    image = Image.byId(image_id)
    imagePart = Partition.byId(part_id)
    fsEle = FileSysEle.fromImagePath(image.path, imagePart, image.bps, file_path)
    
    # Do something for directory handling here, not sure what yet
    return render_template('analysis.html', image=image, partition=imagePart, file_path=file_path)


class DbSynch:
    __not_in_db__ = []
    __not_on_disk__ = []

    @classmethod
    def is_synch_db(cls):
        cls.disk_synch()
        return Image.imageCount() != IMAGE_DIR.imageCount()

    @staticmethod
    def disk_synch():
        IMAGE_DIR = ImageDir.fromRootDir(app.config[ConfKey.IMAGE_DIR])

    @classmethod
    def synch_db(cls):
        if not cls.is_synch_db():
            return
        # Deal with images not in the database first
        cls.images_not_in_db()
        for image in cls.__not_in_db__:
            logging.info("Adding image: " + image.getPath() + " to database.")
            modelImage = Image(**image.toImageDbMap())
            Image.addImage(modelImage)
            ImageFile.populateParts(image)
            for part in image.getPartitions():
                Partition.addPart(Partition(**part.toPartDbMap(modelImage.id)))

        for image in cls.__not_on_disk__:
            logging.warn("Image: " + image.path + " appears to have been deleted from disk.");

    @classmethod
    def images_not_in_db(cls):
        del cls.__not_in_db__[:]
        for image in IMAGE_DIR.images:
            db_image = Image.byPath(image.getPath())
            if db_image is None:
                logging.debug("Image: " + image.getPath() + " not in database.")
                cls.__not_in_db__.append(image)

    @classmethod
    def images_not_on_disk(cls):
        del cls.__not_on_disk__[:]
        for image in Image.images():
            if not os.path.isfile(image.path):
                 logging.debug("Image: " + image.path + " is no longer on disk.")
                 cls.__not_on_disk__.append(image)
