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
"""Utiltiies module, a home to utility classes and methods."""
import hashlib
import os.path
import magic

MIME_IDENT = magic.Magic(mime=True)

# TODO: Make this a resource that's loaded at runtime so easy to add MIME types
MIME_TO_EXT = {
    "application/msword": "doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.template": "docx",
    "message/rfc822": "eml",
    "application/epub+zip": "epub",
    "application/json": "json",
    "text/html": "html",
    "application/xhtml+xml": "html",
    "application/vnd.oasis.opendocument.text": "odt",
    "application/vnd.oasis.opendocument.spreadsheet": "ods",
    "application/vnd.oasis.opendocument.presentation": "odp",
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": "pptx",
    "application/vnd.openxmlformats-officedocument.presentationml.template": "pptx",
    "application/postscript": "ps",
    "text/plain": "txt",
    "application/vnd.ms-excel": "xls",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx"
}


def identify_mime_path(apath):
    """Perform Python Magic identification."""
    if not apath or not os.path.isfile(apath):
        raise ValueError("Arg path must be an exisiting file.")
    mime_string = MIME_IDENT.from_file(apath)
    return mime_string

def sha1_path(apath):
    """Return the SHA1 of the file at apath."""
    return _hashpath(apath, hashlib.sha1())

def _hashpath(apath, hasher):
    """Calculates the digest of the file at apath using the supplied hasher which
    should implement update(buffer) and hexdigest() methods.
    """
    with open(apath, 'rb') as afile:
        return _hashfile(afile, hasher)

def sha1_file(afile, blocksize=65536):
    """Calculates the SHA1 of afile."""
    return _hashfile(afile, hashlib.sha1(), blocksize)

def _hashfile(afile, hasher, blocksize=65536):
    """Calculates the digest of afile using the supplied hasher which should
    implement update(buffer) and hexdigest() methods.
    """
    buf = afile.read(blocksize)
    while buf:
        hasher.update(buf)
        buf = afile.read(blocksize)
    afile.seek(0)
    return hasher.hexdigest()

def map_mime_to_ext(mime_type):
    """Performs MIME type to extension mapping, used to pass file type to Textract."""
    if not mime_type:
        return None
    return MIME_TO_EXT.get(mime_type, None)
