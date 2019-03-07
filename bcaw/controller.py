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
"""NLP markup"""
import spacy
from spacy import displacy

"""Controller module, handles incoming HTTP requests and routing."""
import logging
import os
import urllib
from flask import render_template, send_file, send_from_directory
from flask import request, abort

from .bcaw import APP
from .const import MimeTypes
from .disk_utils import FileSysEle
from .model import Image, Partition, FileElement, ByteSequence, Group
from .text_indexer import ImageIndexer, FullTextSearcher

ROUTES = True

# Load the English language model
# TODO: configuration for language model selection
nlp = spacy.load('en')

@APP.route('/')
def bcaw_home():
    """BCAW application home page."""
    # Render the home page template with a list of images
    return render_template('groups.html', groups=Group.all())

@APP.route('/status')
def bcaw_status():
    """BCAW staus page."""
    # Render the home page template with a list of images
    total_size = 0
    for image in Image.all():
        total_size += image.byte_sequence.size
    return render_template('status.html', group_count=Group.count(), image_count=Image.count(),
                           total_size=total_size)

@APP.route('/search')
def full_text_search():
    """Perform full text search and return results."""
    search_text = request.args.get('search_text', '')
    with FullTextSearcher(APP.config['LUCENE_INDEX_DIR']) as searcher:
        results = searcher.retrieve(search_text)
    byte_sequences = ByteSequence.in_sha1_set(results.keys())
    logging.info("Lucene returns %d results.", len(results))
    return render_template('search_results.html', search_text=search_text,
                           byte_sequences=byte_sequences, hit_counts=results)

@APP.route('/group/<group_id>/')
def group_images(group_id):
    """BCAW application home page."""
    group = Group.by_id(group_id)
    # Render the home page template with a list of images
    return render_template('images.html', group=group, db_images=group.images)

@APP.route('/image')
def bcaw_images():
    """List all images in the database."""
    # Render the home page template with a list of images
    return render_template('images.html', db_images=Image.all())

@APP.route('/image/<image_id>/')
def image_meta(image_id):
    """Page listing the partition details for on image, retrieved from DB."""
    image = _found_or_404(Image.by_id(image_id))
    logging.debug("Getting parts for image: %s", image.name)
    return render_template('partitions.html', image=image, partitions=image.get_partitions())

# TODO - Check why change to raw was made on 6/12/2018. Switched back for now.
#@APP.route('/image/<image_id>/raw')
@APP.route('/image/data/<image_id>/')
def image_dnld(image_id):
    """Image download request, returns the image binary"""
    image = _found_or_404(Image.by_id(image_id))
    parent = os.path.abspath(os.path.join(image.path, os.pardir))
    return send_from_directory(parent, image.name, as_attachment=True)


@APP.route('/image/<image_id>/table/<part_table>/slot/part_slot')
def part_root(image_id, part_table, part_slot):
    """Displays the root directory of a the chosen partition."""
    return file_handler(image_id, part_table, part_slot, "/")

#@APP.route('/image/<image_id>/table/<part_table>/slot/<part_slot>/',
#           defaults={'encoded_filepath': '/'})
#@APP.route('/image/<image_id>/table/<part_table>/slot/<part_slot>/<path:encoded_filepath>/')
@APP.route('/image/<image_id>/table/<part_table>/slot/<part_slot>/',
            defaults={'encoded_filepath': '/', 'view_type': ''})
@APP.route('/image/<image_id>/table/<part_table>/slot/<part_slot>/<path:encoded_filepath>',
            defaults={'view_type': ''})
@APP.route('/image/<image_id>/table/<part_table>/slot/<part_slot>/<path:encoded_filepath>/<string:view_type>')
def file_handler(image_id, part_table, part_slot, encoded_filepath, view_type):
    """Display page for a file system element.
    If the element is a directory then the page displays the directory listing
    as read from the disk image.
    If a file is selected the files contents as a binary payload is sent in
    the Response.
    """
    file_path = urllib.unquote(encoded_filepath)
    partition = _found_or_404(Partition.by_image_table_and_slot(image_id, part_table, part_slot))
    fs_ele = _found_or_404(FileSysEle.from_partition(partition, file_path))
    # Check if we have a directory
    if fs_ele.is_directory:
        # Render the dir listing template
        return _render_directory(partition, file_path)

    # Its a file, we'll need a temp file to analyse or serve
    temp_file = FileSysEle.create_temp_copy(partition, fs_ele)
    # Get the byte stream object and index it.
    byte_sequence, full_text =\
            ImageIndexer.get_path_details(temp_file, os.path.abspath(fs_ele.path))

    # Build the NLP object from extracted full_text, generate entity markup
    full_text_nlp_obj = nlp(unicode(full_text, 'utf-8'))
    full_text_entity_html = displacy.render(full_text_nlp_obj, style='ent', page=False)

    # Check whether this path has been indexed and the results are in the DB
    file_element = FileElement.by_partition_and_path(partition, file_path)
    if file_element is None:
        # If not then add the path and p
        file_element = FileElement(file_path, partition, byte_sequence)

    # Is this a blob request
    if request_wants_binary():
        return send_file(temp_file, mimetype=byte_sequence.mime_type,
                         as_attachment=True, attachment_filename=fs_ele.name)

    # Return correct view depending on URL parameter
    if view_type == 'text-view': 
        return render_template('text_analysis.html', image=partition.image, partition=partition,
                               file_path=file_path, fs_ele=fs_ele, file_element=file_element,
                               full_text=full_text)
    else:
        return render_template('entity_analysis.html', image=partition.image, partition=partition,
                               file_path=file_path, fs_ele=fs_ele, file_element=file_element,
                               full_text=full_text_entity_html)

    
#    return render_template('analysis.html', image=partition.image, partition=partition,
#                           file_path=file_path, fs_ele=fs_ele, file_element=file_element,
#                           full_text=full_text_entity_html)

@APP.route('/raw/<image_id>/table/<part_table>/slot/<part_slot>/',
           defaults={'encoded_filepath': '/'})
@APP.route('/raw/<image_id>/table/<part_table>/slot/<part_slot>/<path:encoded_filepath>/')
def download_file(image_id, part_table, part_slot, encoded_filepath):
    """Download the raw bytes for a given file."""

    file_path = urllib.unquote(encoded_filepath)
    partition = _found_or_404(Partition.by_image_table_and_slot(image_id, part_table, part_slot))
    fs_ele = _found_or_404(FileSysEle.from_partition(partition, file_path))
    # Check if we have a directory
    if fs_ele.is_directory:
        # If so raise 404
        abort(404)

    # Its a file then send the bytes
    temp_file = FileSysEle.create_temp_copy(partition, fs_ele)
    byte_sequence = ByteSequence.from_path(temp_file)

    return send_file(temp_file, mimetype=byte_sequence.mime_type,
                     as_attachment=True, attachment_filename=fs_ele.name)

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
