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
# utils.py: various classless utilities, mostly disk based
#
"""
Disk based utilites for handling disk images.
"""
import logging
import os
import ntpath
import datetime
import subprocess
import tempfile
import time
from mimetypes import MimeTypes
import xml.etree.ElementTree as ET
import pytsk3
from const import Extns, ImgFlds, ExcepMess, EwfTags, EwfTagMap
from const import PartFlds, Defaults, FileExtns, PathChars


class ImageDir(object):
    """Class that encapsulates a root directory containing disk images.
    """
    def __init__(self, root, images):
        self.root = root
        self.images = images

    def getImages(self):
        return self.images

    def imageCount(self):
        return len(self.images)

    @classmethod
    def fromRootDir(cls, root):
        root = root if root.endswith(os.path.sep) else root + os.path.sep
        images = []
        logging.info("Scanning " + root + " for disk images.")
        for file_found in os.listdir(root):
            if cls.is_image(file_found):
                logging.info("Found image file: " + file_found)
                images.append(ImageFile.fromFile(root + file_found))
        imageDir = cls(root, images)
        return imageDir

    @staticmethod
    def is_image(to_check):
        """
        Checks if the supplied file name has a supported extension.
        DOCTESTS:
        >>> ImageDir.is_image('name.E01')
        True
        >>> ImageDir.is_image('name.e01')
        True
        >>> ImageDir.is_image('name.DD')
        True
        >>> ImageDir.is_image('name.ddd')
        False
        >>> ImageDir.is_image('name.pdf')
        False
        >>> ImageDir.is_image('name.pdf')
        False
        >>> ImageDir.is_image('name.xml')
        False
        """
        return os.path.splitext(to_check)[1] in Extns.SUPPORTED

    @staticmethod
    def is_sysmeta(image):
        """
        Checks if the supplied file name has an extension suggesting that
        system metadata can be extracted from it.
        DOCTESTS:
        >>> ImageDir.is_image('name.E01')
        True
        >>> ImageDir.is_image('name.e01')
        True
        >>> ImageDir.is_image('name.AFF')
        True
        >>> ImageDir.is_image('name.aff')
        True
        >>> ImageDir.is_image('name.DD')
        True
        >>> ImageDir.is_image('name.ddd')
        False
        >>> ImageDir.is_image('name.pdf')
        False
        >>> ImageDir.is_image('name.pdf')
        False
        >>> ImageDir.is_image('name.xml')
        False
        """
        return os.path.splitext(image)[1] in Extns.META

    @staticmethod
    def is_raw(image):
        """
        Checks if the supplied file name has a raw image type extension.
        DOCTESTS:
        >>> ImageDir.is_image('name.raw')
        True
        >>> ImageDir.is_image('name.RAW')
        True
        >>> ImageDir.is_image('name.AFF')
        True
        >>> ImageDir.is_image('name.iso')
        True
        >>> ImageDir.is_image('name.ISO')
        True
        >>> ImageDir.is_image('name.DD')
        True
        >>> ImageDir.is_image('name.ddd')
        False
        >>> ImageDir.is_image('name.iSo')
        False
        >>> ImageDir.is_image('name.pdf')
        False
        >>> ImageDir.is_image('name.xml')
        False
        """
        return os.path.splitext(image)[1] in Extns.RAW

class ImageFile(object):

    def __init__(self, path, ewf_file=None, dfxml_file=None):
        self.path = path
        self.name = ntpath.basename(path)
        self.ewf_file = ewf_file if ewf_file is not None else ''
        self.dfxml_file = dfxml_file if dfxml_file is not None else ''
        self.__partitions__ = []

    def getPath(self):
        return self.path

    def getEwfFile(self):
        return self.ewf_file

    def hasEwf(self):
        return self.ewf_file != ''

    def getDfXmlFile(self):
        return self.dfxml_file

    def hasDfXml(self):
        return self.dfxml_file != ''

    def isEwf(self):
        return self.name.endswith(Extns.E01) or self.name.endswith(Extns.E01.upper())

    def getNumPartitions(self):
        return len(self.__partitions__)

    def getPartitions(self):
        return self.__partitions__

    def toImageDbMap(self):
        ret_val = ImgFlds.DEFAULT
        if self.isEwf():
            if not self.hasEwf():
                self.__class__.genEwfFile(self)
            ret_val = ImageFile.ewfToImageTableMap(self.ewf_file)
        ret_val[ImgFlds.PATH] = self.path
        ret_val[ImgFlds.NAME] = self.name
        return ret_val

    @classmethod
    def fromFile(cls, source_file):
        if not os.path.isfile(source_file):
            return
        ewf_file = source_file + Extns.XML if os.path.isfile(source_file + Extns.XML) else ''
        dfxml_file = source_file + \
            Extns.DFXML if os.path.isfile(source_file + Extns.DFXML) else ''
        imageFile = cls(source_file, ewf_file, dfxml_file)
        return imageFile

    @staticmethod
    def ewfToImageTableMap(xmlfile):
        logging.debug("Parsing XML File: " + xmlfile)
        if xmlfile == None or os.stat(xmlfile).st_size == 0:
            # It could be a raw image which has no metadata. Still we need to
            # create the image table for indexing purpose. Create a table with
            # dummy info.
            return ImgFlds.DEFAULT
        try:
            tree = ET.parse(xmlfile)
        except IOError, e:
            logging.error(ExcepMess.PARSING, xmlfile, e)
            return

        root = tree.getroot()  # root node
        retVal = mapped_dict_from_element(
            root, EwfTags.PARENTS, EwfTagMap.LOOKUP)
        retVal[ImgFlds.ACQUIRED] = date_string_to_date(
            retVal[ImgFlds.ACQUIRED])
        retVal[ImgFlds.SYS_DATE] = date_string_to_date(
            retVal[ImgFlds.SYS_DATE])
        return retVal

    @staticmethod
    def genEwfFile(imageFile):
        if imageFile.isEwf():
            ewfinfo_xml = imageFile.path + Extns.XML
            if not os.path.exists(ewfinfo_xml):
                logging.info("Generating EWF for image: " +
                             imageFile.getPath())
                cmd = "ewfinfo -f dfxml " + imageFile.path + " > " + ewfinfo_xml
                logging.debug('CMD: %s for xmlfile: %s', cmd, ewfinfo_xml)
                proc = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                proc.wait()
            imageFile.ewf_file = ewfinfo_xml

    @staticmethod
    def populateParts(imageFile):
        logging.debug("Getting image info for: " + imageFile.path)
        image_info = pytsk3.Img_Info(imageFile.path)
        try:
            volume_info = pytsk3.Volume_Info(image_info)
        except:
            logging.info("Failed to get Volume Info for: " + imageFile.path)
            # pytsk3.Volume_Info works only with file systems which have partition
            # defined. For file systems like FAT12, with no partition info, we need
            # to handle in an exception.
            try:
                fs_info = pytsk3.FS_Info(image_info, offset=0)
            except:
                # Botch by populating with file system details
                imageFile.__partitions__.append(
                    ImagePart(-1, -1, -1, "Error Parsing"))
                return

            if fs_info.info.ftype == pytsk3.TSK_FS_TYPE_FAT12:
                fs_desc = "FAT12 file system"
            elif fs_info.info.ftype == pytsk3.TSK_FS_TYPE_ISO9660_DETECT:
                fs_desc = "ISO file system"
            else:
                fs_desc = "Unknown file system"
            # Botch by populating with file system details
            imageFile.__partitions__.append(ImagePart(0, 0, 0, fs_desc))
            return

        # Loop through the partition info found
        logging.info("Got image info for: " + imageFile.path)
        logging.debug(volume_info)
        for part in volume_info:
            # The slot_num field of volume object has a value of -1
            # for non-partition entries - like Unallocated partition
            # and Primary and extended tables. So we will look for this
            # field to be >=0 to count partitions with valid file systems
            if part.slot_num >= 0:
                # Add the entry to the List of dictionaries, partDictList.
                # The list will have one dictionary per partition. The image
                # name is added as the first element of each partition to
                # avoid a two-dimentional list.
                # Open the file system for this image at the extracted
                # start_offset.
                try:
                    fs_info = pytsk3.FS_Info(image_info, offset=(part.start * 512))
                except:
                    # Exception, log and loop
                    logging.warn("Sleuth toolkit exception thrown getting partition: " +
                                 str(part.slot_num) + " for image: " + imageFile.path)
                    continue

                logging.info("Adding partition: " + part.desc +
                             " for image: " + imageFile.path)
                imageFile.__partitions__.append(
                    ImagePart(part.addr, part.slot_num, part.start, part.desc))


class ImagePart(object):

    def __init__(self, addr, slot, start, desc):
        self.addr = addr
        self.slot = slot
        self.start = start
        self.desc = desc

    def toPartDbMap(self, image_id):
        return {
            PartFlds.ADDR: self.addr,
            PartFlds.SLOT: self.slot,
            PartFlds.START: self.start,
            PartFlds.DESC: self.desc,
            PartFlds.IMAGE: image_id
        }


class FileSysEle(object):
    # def __init__(self, path, size, mode, mtime, atime, ctime, addr, isDir,
    # isDeleted):

    def __init__(self, path, size, mode, mtime, atime, ctime, addr, isDir, isDeleted, isCandidate):
        self.path = path
        self.name = ntpath.basename(path)
        self.size = size
        self.mode = mode
        self.mtime = datetime.datetime.fromtimestamp(
            mtime).isoformat() if mtime != 0 else Defaults.NA
        self.atime = datetime.datetime.fromtimestamp(
            atime).isoformat() if atime != 0 else Defaults.NA
        self.ctime = datetime.datetime.fromtimestamp(
            ctime).isoformat() if ctime != 0 else Defaults.NA
        self.addr = addr
        self.isDir = isDir
        self.isDeleted = isDeleted
        self.isCandidate = isCandidate

    def isDirectory(self):
        return self.isDir

    @classmethod
    def rootElement(cls):
        rootObj = cls('/', 0, '', 0, 0, 0, -1, True, False, False)
        return rootObj

    @classmethod
    def fromImagePath(cls, image_path, imagePart, block_size, path):
        parent_path, file_name = os.path.split(path)
        if is_root(parent_path, file_name):
            rootEle = cls.rootElement()
            return rootEle
        return cls.getFileFromDir(image_path, imagePart.start, block_size,
                                  parent_path, file_name)

    @classmethod
    def getFileFromDir(cls, image_path, start, block_size, parent_path,
                       file_name):
        file_sys_info = cls.getFileSystemInfo(image_path, start, block_size)
        parent_dir = file_sys_info.open_dir(path=parent_path)
        for child_file in parent_dir:
            if (child_file.info.meta != None) and (child_file.info.name.name == file_name):
                logging.debug("Found file: " +
                              child_file.info.name.name + " against " + file_name)
                return cls.fromFileInfo(parent_path, child_file.info)
        return None

    @classmethod
    def fromFileInfo(cls, path, info):
        """Creates a new FileSysEle instance from the supplied params"""
        ele = cls(path + info.name.name, info.meta.size, info.meta.mode,
                  info.meta.mtime, info.meta.atime, info.meta.ctime,
                  info.meta.addr, is_dir(info.meta.type), is_deleted(info),
                  is_candidate(info))
        return ele

    @staticmethod
    def getFileSystemInfo(image_path, start, block_size):
        logging.debug("Getting Image info for:" + image_path +
                      " start:" + str(start) + " size:" + str(block_size))
        image_info = pytsk3.Img_Info(image_path)
        # Open the file system for this image at the extracted
        # start_offset.
        logging.debug("Getting Image Info offset:" + str(start * block_size))
        fs = pytsk3.FS_Info(image_info, offset=(start * block_size))
        return fs

    @classmethod
    def listFiles(cls, image_path, imagePart, block_size, path):
        file_list = []
        file_sys_info = cls.getFileSystemInfo(
            image_path, imagePart.start, block_size)
        directory = file_sys_info.open_dir(path=path)
        for listed_file in directory:
            if listed_file.info.meta != None:
                file_list.append(FileSysEle.fromFileInfo(
                    '/' + path + '/', listed_file.info))
        return file_list

    @classmethod
    def createTempCopy(cls, image_path, start, block_size, fsEle):
        """Creates a temp file copy of a file from the specified image."""
        mime_type = cls.GuessMimeType(fsEle.name)
        generator = cls.payloadGenerator(image_path, start, block_size, fsEle)

        # Open with a named temp file
        with tempfile.NamedTemporaryFile(delete=False) as temp:
            for data in generator:
                temp.write(data)
                temp.flush()
            # Return an opened temp file
            return temp.name, mime_type

    @classmethod
    def payloadGenerator(cls, image_path, start, block_size, fsEle):
        """Generator used to loop through a file's content."""
        logging.debug("Getting image file information")
        file_sys_info = cls.getFileSystemInfo(image_path, start, block_size)
        image_file = file_sys_info.open_meta(inode=fsEle.addr)
        # Set up the date copy process vars
        offset = 0
        file_size = image_file.info.meta.size
        buff_size = 1024 * 1024
        # Loop through data read and yield it 1MB chunk at a time
        logging.debug("Starting delivery loop, file_size:" + str(file_size) + " Bytes.")
        while offset < file_size:
            available = min(buff_size, file_size - offset)
            data = image_file.read_random(offset, available)
            offset += len(data)
            # If no data then break the generator loop
            if not data:
                break
            yield data

    @classmethod
    def GuessMimeType(cls, file_name):
        """Function to guess the MIME type of a file by filename extension.
        DOCTESTS:
        >>> FileSysEle.GuessMimeType('name.pdf')
        'application/pdf'
        >>> FileSysEle.GuessMimeType('name.docx')
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        >>> FileSysEle.GuessMimeType('name.xls')
        'application/vnd.ms-excel'
        >>> FileSysEle.GuessMimeType('name.txt')
        'text/plain'
        """
        return MimeTypes().guess_type(file_name)[0]

def mapped_dict_from_element(root, parent_tags, tag_dict):
    """
    Recursively parses an XML structure and maps tag names / tag values to the
    equivalent database field names. This info is stacked up in a dictionary that
    the function returns.
    parent_tags: a list of tag values that are parents and should be recursed into
    tag_dict: a dictionary of tag-values that map to the database field name
    """
    mapped_dict = dict()
    for child in root:
        # Parent element so recurse and merge the returned map
        if child.tag in parent_tags:
            child_dict = mapped_dict_from_element(child, parent_tags, tag_dict)
            mapped_dict.update(child_dict)
        # Mapped element, add the value to the returned dict
        elif child.tag in tag_dict:
            field = tag_dict[child.tag]
            mapped_dict[field] = child.text
    return mapped_dict

def date_string_to_date(date_string):
    return datetime.datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%S")

def strip_mtime(mtime):
    return time.strftime("%FT%TZ", time.gmtime(mtime))

def is_deleted(info):
    return int(info.meta.flags) & 0x01 == 0


def is_candidate(info):
    """Check if this is a candidate for text extraction
    Get just the extension (this is dirty, also gets dotfile names now)
    """
    file_ext = (info.name.name).rsplit('.', 1)
    if len(file_ext) > 1:
        return file_ext[1] in FileExtns.ALLEXT
        #logging.debug("End after split:" + fa[1])
    else:
        return False


def is_dir(meta_type):
    """Checks the meta_type from image info to see if the element is a directory
    """
    return meta_type == 2

def is_root(parent, file_to_check):
    return (parent in PathChars.SEPS) and not file_to_check
