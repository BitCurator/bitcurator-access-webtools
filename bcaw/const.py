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
"""Constants used across BitCurator modules.
These need to map to the names used in the default config file, but better
than multiple hardcoded strings in code.
"""
import datetime

ENV_CONF_PROFILE = 'BCAW_CONFIG'
ENV_CONF_FILE = 'BCAW_CONF_FILE'

class ConfKey(object):
    """Config key string constatnts"""
    LOG_FORMAT = 'LOG_FORMAT'
    LOG_FILE = 'LOG_FILE'
    IMAGE_DIR = 'IMAGE_DIR'

class Defaults(object):
    """Default values"""
    NA = 'N/A'
    NULL_MD5 = 'd41d8cd98f00b204e9800998ecf8427e'

class Extns(object):
    """File extensions for disk image types and XML."""
    E01 = '.e01'
    AFF = '.aff'
    RAW = '.raw'
    DD = '.dd'
    ISO = '.iso'
    XML = '.xml'
    DFXML = '_dfxml' + XML
    # list of image types supporting system metadata
    META = [E01, E01.upper(), AFF, AFF.upper()]
    RAW_TYPES = [RAW, RAW.upper(), DD, DD.upper(), ISO, ISO.upper()]
    SUPPORTED = META + RAW_TYPES
    IGNORED = [XML, XML.upper()]
    FORMAT_DETAILS = {
        DD: "Raw",
        AFF: "Advanced forensic",
        RAW: "Raw",
        E01: "EnCase 6",
        ISO: "ISO"
    }

class MimeTypes(object):
    BINARY = 'application/octet-stream'
    HTML = 'text/html'

class FileExtns(object):
    """Extensions for text extraction support (via textract)
    See http://textract.readthedocs.io/en/stable/ for deps to support these
    """
    BASEEXT = ['csv', 'doc', 'docx', 'eml', 'epub', 'gif', 'jpg', \
               'jpeg', 'json', 'html', 'htm', 'mp3', 'msg', 'odt', \
               'ogg', 'pdf', 'png', 'pptx', 'ps', 'rtf', 'tiff', \
               'tif', 'txt', 'wav', 'xlsx', 'xls']
    # Lower and upper case list
    ALLEXT = BASEEXT + [x.upper() for x in BASEEXT]

class ImgDetsFlds(object):
    """Field names for mappings from EWF tags"""
    ACQUIRED = 'acquired'
    SYS_DATE = 'system_date'
    OS = 'operating_system'
    FORMAT = 'image_format'
    MEDIA_TYPE = 'media_type'
    IS_PHYSICAL = 'is_physical'
    MD5 = 'md5'
    DEFAULT = {
        ACQUIRED    : datetime.date.today(),
        SYS_DATE    : datetime.date.today(),
        OS          : Defaults.NA,
        FORMAT      : Defaults.NA,
        MEDIA_TYPE  : Defaults.NA,
        IS_PHYSICAL : False,
        MD5         : Defaults.NULL_MD5
    }

class ImgPropsFlds(object):
    """Field names for mappings from EWF tags"""
    BPS = 'bps'
    SECTORS = 'sectors'
    SIZE = 'size'
    DEFAULT = {
        BPS         : 0,
        SECTORS     : 0,
        SIZE        : 0,
    }

class PathChars(object):
    """File path separator characters"""
    PATH_SEP_FOR = '/'
    PATH_SEP_BACK = '\\'
    SEPS = [PATH_SEP_FOR, PATH_SEP_BACK]


class EwfTags(object):
    """EWF XMl element tags"""
    # Parent tags
    EWINFO = 'ewfinfo'
    ACQ_INFO = 'acquiry_information'
    EWF_INFO = 'ewf_information'
    MEDIA_INF = 'media_information'
    # Array of parent tags
    PARENTS = [EWINFO, ACQ_INFO, EWF_INFO, MEDIA_INF]
    # Tags to be mapped
    # Acquiry info
    ACQ_DATE = 'acquisition_date'
    ACQ_SYS = 'acquisition_system'
    SYS_DATE = 'system_date'
    # EWF Info
    FILE_FORMAT = 'file_format'
    # Media Info
    MEDIA_TYPE = ImgDetsFlds.MEDIA_TYPE
    IS_PHYSICAL = ImgDetsFlds.IS_PHYSICAL
    BPS = 'bytes_per_sector'
    SECTORS = 'number_of_sectors'
    MEDIA_SIZE = 'media_size'
    HASH_DIGEST = 'hashdigest'

class EwfDetailsTagMap(object):
    """Maps Expert Witness Format tags to DB Image table fields"""
    LOOKUP = {
        EwfTags.ACQ_DATE    : ImgDetsFlds.ACQUIRED,
        EwfTags.SYS_DATE    : ImgDetsFlds.SYS_DATE,
        EwfTags.ACQ_SYS     : ImgDetsFlds.OS,
        EwfTags.FILE_FORMAT : ImgDetsFlds.FORMAT,
        EwfTags.MEDIA_TYPE  : ImgDetsFlds.MEDIA_TYPE,
        EwfTags.IS_PHYSICAL : ImgDetsFlds.IS_PHYSICAL,
        EwfTags.HASH_DIGEST : ImgDetsFlds.MD5
    }

class EwfPropertiesTagMap(object):
    """Maps Expert Witness Format tags to DB Image table fields"""
    LOOKUP = {
        EwfTags.BPS         : ImgPropsFlds.BPS,
        EwfTags.SECTORS     : ImgPropsFlds.SECTORS,
        EwfTags.MEDIA_SIZE  : ImgPropsFlds.SIZE
    }

# Exceptions
class ExcepMess(object):
    """Messages for exceptions"""
    PARSING = 'Exception when parsing %s: %s'
