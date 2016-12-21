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
import logging, os, ntpath, datetime, subprocess, time
from mimetypes import MimeTypes
from bcaw.const import *
import pytsk3
import xml.etree.ElementTree as ET

class ImageDir(object):
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
        for file in os.listdir(root):
            if cls.is_image(file):
                logging.info("Found image file: " + file)
                images.append(ImageFile.fromFile(root + file))
        imageDir = cls(root, images)
        return imageDir

    @staticmethod
    def is_image(file):
        img_name, img_extension = os.path.splitext(file)
        return img_extension in Extns.SUPPORTED

    @staticmethod
    def is_sysmeta(image):
        imgname, img_extension = os.path.splitext(image)
        return img_extension in Extns.META

    @staticmethod
    def is_raw(image):
        imgname, img_extension = os.path.splitext(image)
        return img_extension in Extns.RAW

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
    def fromFile(cls, file):
        if not os.path.isfile(file):
            return
        ewf_file = file + Extns.XML if os.path.isfile(file + Extns.XML) else ''
        dfxml_file = file + Extns.DFXML if os.path.isfile(file + Extns.DFXML) else ''
        imageFile = cls(file, ewf_file, dfxml_file)
        return imageFile

    @staticmethod
    def ewfToImageTableMap(xmlfile):
        logging.debug("Parsing XML File: " + xmlfile)
        if xmlfile == None:
            # It could be a raw image which has no metadata. Still we need to
            # create the image table for indexing purpose. Create a table with
            # dummy info.
            return ImgFlds.DEFAULT
        try:
            tree = ET.parse(xmlfile)
        except IOError, e:
            logging.error(ExcepMess.PARSING, xmlfile, e)
            return

        root = tree.getroot() # root node
        retVal = mapped_dict_from_element(root, EwfTags.PARENTS, EwfTagMap.LOOKUP)
        retVal[ImgFlds.ACQUIRED] = date_string_to_date(retVal[ImgFlds.ACQUIRED])
        retVal[ImgFlds.SYS_DATE] = date_string_to_date(retVal[ImgFlds.SYS_DATE])
        return retVal

    @staticmethod
    def genEwfFile(imageFile):
        if imageFile.isEwf():
            ewfinfo_xml = imageFile.path + Extns.XML
            if not os.path.exists(ewfinfo_xml):
                logging.info("Generating EWF for image: " + imageFile.getPath())
                cmd = "ewfinfo -f dfxml " + imageFile.path + " > " + ewfinfo_xml
                logging.debug('CMD: %s for xmlfile: %s', cmd, ewfinfo_xml)
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
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
                fs = pytsk3.FS_Info(image_info, offset=0)
            except:
                # Botch by populating with file system details
                imageFile.__partitions__.append(ImagePart(-1, -1, -1, "Error Parsing"))
                return

            if fs.info.ftype == pytsk3.TSK_FS_TYPE_FAT12:
                fs_desc = "FAT12 file system"
            elif fs.info.ftype == pytsk3.TSK_FS_TYPE_ISO9660_DETECT:
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
                    fs = pytsk3.FS_Info(image_info, offset=(part.start * 512))
                except:
                    # Exception, log and loop
                    logging.warn("Sleuth toolkit exception thrown getting partition: " + str(part.slot_num) + " for image: " + imageFile.path)
                    continue

                logging.info("Adding partition: " + part.desc + " for image: " + imageFile.path)
                imageFile.__partitions__.append(ImagePart(part.addr, part.slot_num, part.start, part.desc))

class ImagePart(object):
    def __init__(self, addr, slot, start, desc):
        self.addr = addr
        self.slot = slot
        self.start = start
        self.desc = desc

    def toPartDbMap(self, image_id):
        return {
            PartFlds.ADDR  : self.addr,
            PartFlds.SLOT  : self.slot,
            PartFlds.START : self.start,
            PartFlds.DESC  : self.desc,
            PartFlds.IMAGE : image_id
        }

class FileSysEle(object):
    #def __init__(self, path, size, mode, mtime, atime, ctime, addr, isDir, isDeleted):
    def __init__(self, path, size, mode, mtime, atime, ctime, addr, isDir, isDeleted, isCandidate):
        self.path = path
        self.name = ntpath.basename(path)
        self.size = size
        self.mode = mode
        self.mtime = datetime.datetime.fromtimestamp(mtime).isoformat() if mtime != 0 else Defaults.NA
        self.atime = datetime.datetime.fromtimestamp(atime).isoformat() if atime != 0 else Defaults.NA
        self.ctime = datetime.datetime.fromtimestamp(ctime).isoformat() if ctime != 0 else Defaults.NA
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
        if (is_root(parent_path, file_name)):
            rootEle = cls.rootElement()
            return rootEle
        return cls.getFileFromDir(image_path, imagePart.start, block_size, parent_path, file_name)

    @classmethod
    def getFileFromDir(cls, image_path, start, block_size, parent_path, file_name):
        file_sys_info = cls.getFileSystemInfo(image_path, start, block_size)
        parent_dir = file_sys_info.open_dir(path=parent_path)
        for file in parent_dir:
            if (file.info.meta != None) and (file.info.name.name == file_name):
                logging.debug("Found file: " + file.info.name.name + " against " + file_name)
                return cls.fromFileInfo(parent_path, file.info)
        return None

    @classmethod
    def fromFileInfo(cls, path, info):
        ele = cls(path + info.name.name, info.meta.size, info.meta.mode, info.meta.mtime, info.meta.atime, info.meta.ctime, info.meta.addr, is_dir(info.meta.type), is_deleted(info), is_candidate(info))
        return ele

    @staticmethod
    def getFileSystemInfo(image_path, start, block_size):
        logging.debug("Getting Image info for:" + image_path + " start:" + str(start) + " size:" + str(block_size))
        image_info = pytsk3.Img_Info(image_path)
        # Open the file system for this image at the extracted
        # start_offset.
        logging.debug("Getting Image Info offset:" + str(start * block_size))
        fs = pytsk3.FS_Info(image_info, offset=(start * block_size))
        return fs

    @classmethod
    def listFiles(cls, image_path, imagePart, block_size, path):
        file_list = []
        file_sys_info = cls.getFileSystemInfo(image_path, imagePart.start, block_size)
        directory = file_sys_info.open_dir(path=path)
        for file in directory:
            if file.info.meta != None:
                file_list.append(FileSysEle.fromFileInfo('/' + path + '/', file.info))
        return file_list

    @classmethod
    def getPayload(cls, image_path, start, block_size, fsEle):
        file_sys_info = cls.getFileSystemInfo(image_path, start, block_size)
        file = file_sys_info.open_meta(inode=fsEle.addr)

        # Read data and store it in a string
        offset = 0
        size = file.info.meta.size
        BUFF_SIZE = 1024 * 1024

        total_data = ""
        while offset < size:
            available = min(BUFF_SIZE, size - offset)
            data = file.read_random(offset, available)
            if not data:
                break
            offset += len(data)
            total_data = total_data+data

        mime = MimeTypes()
        mime_type, a = mime.guess_type(fsEle.name)
        generator = (cell for row in total_data
                        for cell in row)
        return generator, mime_type

#
# Recursively parses an XML structure and maps tag names / tag values to the
# equivalent database field names. This info is stacked up in a dictionary that
# the fucntion returns.
# parent_tags: a list of tag values that are parents and should be recursed into
# tag_dict: a dictionary of tag-values that map to the database field name
#
def mapped_dict_from_element(root, parent_tags, tag_dict):
    mapped_dict = dict()
    for child in root:
        # Parent element so recurse and merge the returned map
        if (child.tag in parent_tags):
            child_dict = mapped_dict_from_element(child, parent_tags, tag_dict)
            mapped_dict.update(child_dict)
        # Mapped element, add the value to the returned dict
        elif (child.tag in tag_dict):
            field = tag_dict[child.tag]
            mapped_dict[field] = child.text
    return mapped_dict

def date_string_to_date(date_string):
    return datetime.datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%S")

def strip_mtime(mtime):
    return time.strftime("%FT%TZ",time.gmtime(mtime))

def is_deleted(info):
    return (int(info.meta.flags) & 0x01 == 0)

# Check if this is a candidate for text extraction
def is_candidate(info):
    # Get just the extension (this is dirty, also gets dotfile names now)
    fa = (info.name.name).rsplit('.',1)
    if len(fa) > 1:
        return fa[1] in FileExtns.ALLEXT
        #logging.debug("End after split:" + fa[1])
    else: 
        return False

def is_dir(meta_type):
    return (meta_type == 2)

def is_root(parent, file):
    return (parent in PathChars.SEPS) and not file
