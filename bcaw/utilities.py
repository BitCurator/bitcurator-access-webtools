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

class MimeMapper(object):
    """Class that parses MIME to extenion mappings from config file. Used to
    decide which text types are indexed."""
    def __init__(self, config_path=None):
        self.mime_map = MIME_TO_EXT.copy()
        if config_path:
            self.parse_config(config_path)

    def parse_config(self, config_path):
        """Parse the MIME mappings from the JSON file."""
        check_param_not_none(config_path, "config_path")
        try:
            with open(config_path, mode='rb') as config_file:
                self.mime_map = eval(config_file.read())
        except IOError as _e:
            # if silent and e.errno in (errno.ENOENT, errno.EISDIR):
            #     return False
            _e.strerror = 'Unable to load configuration file (%s)' % _e.strerror
            raise

    def get_mime_map(self):
        """Return the GROUPS element for iterating."""
        return self.mime_map

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

def map_mime_to_ext(mime_type, mapper=None):
    """Performs MIME type to extension mapping, used to pass file type to Textract."""
    if not mime_type:
        return None
    lookup_map = MIME_TO_EXT if mapper is None else mapper.get_mime_map()
    return lookup_map.get(mime_type, None)

def check_param_not_none(param, name):
    """Check that the passed param is not None or an empty string.
    Raise a ValueError with the param's name if it is None or an empty string"""
    if not param:
        message_terminator = ' or an empty string.' if isinstance(param, str) else '.'
        raise ValueError("Argument {} can not be None{}".format(name, message_terminator))

def timestamp_fmt(timestamp, show_millis=False):
    """ISO format for timestamps."""
    format_str = "%Y-%m-%d %H:%M:%S.%f" if show_millis else "%Y-%m-%d %H:%M:%S"
    return timestamp.strftime(format_str)

def sizeof_fmt(num, suffix='B'):
    """Format byte size in human readable form.
    from: http://stackoverflow.com/questions/1094841/reusable
    -library-to-get-human-readable-version-of-file-size
    """
    for unit in ['', 'K', 'M', 'G', 'T', 'P', 'E', 'Z']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Y', suffix)
