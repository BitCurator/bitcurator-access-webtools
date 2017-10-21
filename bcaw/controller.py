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
"""Controller module, handles incoming HTTP requests and routing."""
import logging
import os
import urllib
from flask import render_template, send_file, send_from_directory
from flask import request, abort
from textract import process
from textract.exceptions import ExtensionNotSupported

from .bcaw import APP
from .const import ConfKey, MimeTypes
from .disk_utils import ImageDir, ImageFile, FileSysEle
from .model import Image, Partition, FileElement, ByteSequence
from .text_indexer import ImageIndexer
from .utilities import map_mime_to_ext
ROUTES = True

@APP.route('/')
def bcaw_home():
    """BCAW application home page, test DB is synched and display home."""
    # If there's a different number of images on disk than
    # in the DB table it's time to synch
    if DbSynch.is_synch_db():
        DbSynch.synch_db()
    # Render the home page template with a list of images
    return render_template('home.html', db_images=Image.all())

@APP.route('/search')
def full_text_search():
    """Perform full text search and return results."""
    search_text = request.args.get('search_text', '')
    with ImageIndexer(APP.config['LUCENE_INDEX_DIR']) as indexer:
        return indexer.retrieve(search_text)

@APP.route('/image/meta/<image_id>/')
def image_meta(image_id):
    """Image metadata page, retrieves image info from DB and displays it."""
    # Get and test the image
    image = _found_or_404(Image.by_id(image_id))
    return render_template('image.html', image=image)

@APP.route('/image/data/<image_id>/')
def image_dnld(image_id):
    """Image download request, returns the image binary"""
    image = _found_or_404(Image.by_id(image_id))
    parent = os.path.abspath(os.path.join(image.path, os.pardir))
    return send_from_directory(parent, image.name, as_attachment=True)

@APP.route('/image/<image_id>/')
def image_parts(image_id):
    """Page listing the partition details for on image, retrieved from DB."""
    image = _found_or_404(Image.by_id(image_id))
    logging.debug("Getting parts for image: " + image.name)
    for part in image.partitions.all():
        logging.debug("Part " + str(part.id))
    return render_template('partitions.html', image=image, partitions=image.get_partitions())

@APP.route('/image/<image_id>/<part_id>/')
def part_root(image_id, part_id):
    """Displays the root directory of a the chosen partition."""
    return file_handler(image_id, part_id, "/")

@APP.route('/image/<image_id>/<part_id>/', defaults={'encoded_filepath': '/'})
@APP.route('/image/<image_id>/<part_id>/<path:encoded_filepath>/')
def file_handler(image_id, part_id, encoded_filepath):
    """Display page for a file system element.
    If the element is a directory then the page displays the directory listing
    as read from the disk image.
    If a file is selected they files contents as a binary payload is sent in
    the Response.
    """
    file_path = urllib.unquote(encoded_filepath)
    partition = _found_or_404(Partition.by_id(part_id))
    fs_ele = _found_or_404(FileSysEle.from_partition(partition, file_path))
    # Check if we have a directory
    if fs_ele.is_directory:
        # Render the dir listing template
        return _render_directory(partition, file_path)

    # Its a file, we'll need a temp file to analyse or serve
    temp_file = FileSysEle.create_temp_copy(partition, fs_ele)

    file_element = FileElement.by_partition_and_path(partition, file_path)
    if file_element is None:
        byte_sequence = ByteSequence.from_path(temp_file)
        file_element = FileElement(file_path, partition, byte_sequence)
        FileElement.add(file_element)

    # Is this a blob request
    if request_wants_binary():
        return send_file(temp_file, mimetype=FileSysEle.guess_mime_type(fs_ele.name),
                         as_attachment=True, attachment_filename=fs_ele.name)

    extension = map_mime_to_ext(file_element.byte_sequence.mime_type)
    logging.debug("MIME: %s EXTENSION %s SHA1:%s", file_element.byte_sequence.mime_type,
                  extension, file_element.byte_sequence.sha1)
    full_text = "N/A"
    if extension is not None:
        try:
            logging.debug("Textract for doc %s, extension map val %s", file_element.path, extension)
            full_text = process(temp_file, extension=extension, encoding='ascii')
            with ImageIndexer(APP.config['LUCENE_INDEX_DIR']) as indexer:
                indexer.index_text(file_element.byte_sequence.sha1, full_text)
        except ExtensionNotSupported as _:
            logging.exception("Textract extension not supported for ext %s", extension)
            logging.debug("Temp path for file is %s", temp_file)
            full_text = "N/A"
        except:
            logging.exception("Textract unexpectedly failed for temp_file %s", temp_file)
            raise

    return render_template('analysis.html', image=partition.image, partition=partition,
                           file_path=file_path, fs_ele=fs_ele, file_element=file_element,
                           full_text=full_text)

def _render_directory(partition, path):
    # Render the dir listing template
    files = FileSysEle.list_files(partition, path)
    return render_template('directory.html', image=partition.image,
                           partition=partition, files=files)

@APP.errorhandler(404)
def page_not_found(_e):
    """Home of the official 404 handler."""
    return render_template('404.html'), 404

def _found_or_404(test_if_found):
    if test_if_found is None:
        abort(404)
    return test_if_found

def request_wants_binary():
    """Checks the accepts MIME type of the incoming request and returns True
    if the user has requested a blob, i.e. application/octet-stream."""
    best = request.accept_mimetypes.best_match([MimeTypes.BINARY, MimeTypes.HTML])
    return best == MimeTypes.BINARY and request.accept_mimetypes[best] > \
                                        request.accept_mimetypes[MimeTypes.HTML]

class DbSynch(object):
# Keep a list of images
    """Class that synchs images in the application directory with the DB record.
    """
    image_dir = ImageDir.from_root_dir(APP.config[ConfKey.IMAGE_DIR])
    __not_in_db__ = []
    __not_on_disk__ = []

    @classmethod
    def is_synch_db(cls):
        """Returns true if the database needs resynching with file system."""
        cls.disk_synch()
        return Image.count() != DbSynch.image_dir.count()

    @classmethod
    def disk_synch(cls):
        """Updates the list of disk images from the directory listing."""
        cls.image_dir = ImageDir.from_root_dir(APP.config[ConfKey.IMAGE_DIR])

    @classmethod
    def synch_db(cls):
        """Updates the database with images found in the image directory."""
        if not cls.is_synch_db():
            return
        # Deal with images not in the database first
        cls.images_not_in_db()
        for image_file in cls.__not_in_db__:
            logging.info("Adding image: " + image_file.path + " to database.")
            image = image_file.to_model_image()
            Image.add(image)
            ImageFile.populate_parts(image, image_file)
            for part in image_file.get_partitions():
                Partition.add(part)

        for image in cls.__not_on_disk__:
            logging.warn("Image: " + image.path + " appears to have been deleted from disk.")

    @classmethod
    def images_not_in_db(cls):
        """Checks that images on the disk are also on database.
        Missing images are added to a member list,
        """
        del cls.__not_in_db__[:]
        for image in cls.image_dir.images:
            db_image = Image.by_path(image.path)
            if db_image is None:
                logging.debug("Image: " + image.path + " not in database.")
                cls.__not_in_db__.append(image)

    @classmethod
    def images_not_on_disk(cls):
        """Checks that images in the database are also on disk.
        Missing images are added to a member list,
        """
        del cls.__not_on_disk__[:]
        for image in Image.all():
            if not os.path.isfile(image.path):
                logging.debug("Image: " + image.path + " is no longer on disk.")
                cls.__not_on_disk__.append(image)
