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

from bcaw.const import Extns, ImgFlds, ExcepMess, EwfTags, EwfTagMap
from bcaw.const import PartFlds, Defaults, FileExtns, PathChars


class ImageDir(object):
    """Class that encapsulates a root directory containing disk images."""
    def __init__(self, root, images):
        self.root = root
        self.images = images

    def get_images(self):
        """Returns a list of all of the images in the image directory."""
        return self.images

    def image_count(self):
        """Returns the number of images in the directory."""
        return len(self.images)

    @classmethod
    def from_root_dir(cls, root):
        """Returns a new ImageDir instance initialised from the passed directory."""
        root = root if root.endswith(os.path.sep) else root + os.path.sep
        images = []
        logging.info("Scanning " + root + " for disk images.")
        for file_found in os.listdir(root):
            if cls.is_image(file_found):
                logging.info("Found image file: " + file_found)
                images.append(ImageFile.from_file(root + file_found))
        image_dir = cls(root, images)
        return image_dir

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
    """Encapsulates basic properties of an image file."""
    def __init__(self, path, ewf_file=None, dfxml_file=None):
        self.__path = path
        self.name = ntpath.basename(path)
        self.__ewf_file = ewf_file if ewf_file is not None else ''
        self.dfxml_file = dfxml_file if dfxml_file is not None else ''
        self.__partitions__ = []

    @property
    def path(self):
        """Return the path of the image file."""
        return self.__path

    @property
    def ewf_file(self):
        """Return the Expert Witness File if it exists."""
        return self.__ewf_file

    @property
    def has_ewf(self):
        """Returns true if image has an expert witness file, false otherwise."""
        return self.ewf_file != ''

    def get_dfxml_file(self):
        """Returns the image's associated Digital Forensics XML file if one exists."""
        return self.dfxml_file

    def has_dfxml(self):
        """Returns true if this image has an associated Digital Forensics XML file,
        otherwise returns false."""
        return self.dfxml_file != ''

    def is_ewf(self):
        """Returns true if this image is in the Expert Witness Format."""
        return self.name.endswith(Extns.E01) or self.name.endswith(Extns.E01.upper())

    def get_num_partitions(self):
        """Returns the number of partitions for this image."""
        return len(self.__partitions__)

    def get_partitions(self):
        """Returns the set of partitions for this image."""
        return self.__partitions__

    def to_image_db_map(self):
        """Returns the image as a map suitable for database."""
        # Set up a default
        ret_val = ImgFlds.DEFAULT
        if self.is_ewf():
            # Expert witness, if there's no metadata file try generating one
            if not self.has_ewf:
                self.__class__.ewf_file_generator(self)
            # set up return value from map of metadata XML
            ret_val = ImageFile.ewf_to_image_table_map(self.ewf_file)
        # TODO: else:
            # Not an expert witness file, we do what we can
        # Add the path and the name
        ret_val[ImgFlds.PATH] = self.path
        ret_val[ImgFlds.NAME] = self.name
        return ret_val

    @classmethod
    def from_file(cls, source_file):
        """Returns a new Image instance created from source_file."""
        if not os.path.isfile(source_file):
            return
        ewf_file = source_file + Extns.XML if os.path.isfile(source_file + Extns.XML) else ''
        dfxml_file = source_file + \
            Extns.DFXML if os.path.isfile(source_file + Extns.DFXML) else ''
        image_file = cls(source_file, ewf_file, dfxml_file)
        return image_file

    @staticmethod
    def ewf_to_image_table_map(xml_file):
        """Converts and Expert Witness format XML file to a map suitable for the DB."""
        logging.debug("Parsing XML File: " + xml_file)
        if xml_file is None or os.stat(xml_file).st_size == 0:
            # It could be a raw image which has no metadata. Still we need to
            # create the image table for indexing purpose. Create a table with
            # dummy info.
            return ImgFlds.DEFAULT
        try:
            tree = ET.parse(xml_file)
        except IOError, _e:
            logging.error(ExcepMess.PARSING, xml_file, _e)
            return

        root = tree.getroot()  # root node
        ret_val = mapped_dict_from_element(
            root, EwfTags.PARENTS, EwfTagMap.LOOKUP)
        ret_val[ImgFlds.ACQUIRED] = date_string_to_date(
            ret_val[ImgFlds.ACQUIRED])
        ret_val[ImgFlds.SYS_DATE] = date_string_to_date(
            ret_val[ImgFlds.SYS_DATE])
        return ret_val

    @staticmethod
    def ewf_file_generator(image_file):
        """Generates an expert witness format XML file for an image."""
        if image_file.is_ewf():
            ewfinfo_xml = image_file.path + Extns.XML
            if not os.path.exists(ewfinfo_xml):
                logging.info("Generating EWF for image: " +
                             image_file.path)
                cmd = "/usr/local/bin/ewfinfo -f dfxml " + image_file.path
                logging.debug('CMD: %s for xml_file: %s', cmd, ewfinfo_xml)
                flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL  # Refer to "man 2 open".
                mode = 0o666  # Must set mode for www-data to write
                # For security, remove file with potentially elevated mode
                try:
                    os.remove(ewfinfo_xml)
                except OSError:
                    pass
                # Open file descriptor
                umask_original = os.umask(0)
                try:
                    fdesc = os.open(ewfinfo_xml, flags, mode)
                finally:
                    os.umask(umask_original)
                # Open file handle and write to file
                with os.fdopen(fdesc, 'w') as fout:
                    try:
                        procout = subprocess.check_output(cmd, stderr=subprocess.PIPE, shell=True)
                        fout.write(procout)
                    except subprocess.CalledProcessError:
                        logging.exception('FAILED: %s for xml_file: %s', cmd, ewfinfo_xml)
            image_file.ewf_file = ewfinfo_xml

    @staticmethod
    def populate_parts(image_file):
        """Populate partition information for an image from the image file."""
        logging.debug("Getting image info for: " + image_file.path)
        image_info = pytsk3.Img_Info(image_file.path)
        try:
            volume_info = pytsk3.Volume_Info(image_info)
        except:
            logging.info("Failed to get Volume Info for: " + image_file.path)
            # pytsk3.Volume_Info works only with file systems which have partition
            # defined. For file systems like FAT12, with no partition info, we need
            # to handle in an exception.
            try:
                fs_info = pytsk3.FS_Info(image_info, offset=0)
            except:
                # Botch by populating with file system details
                image_file.__partitions__.append(
                    ImagePart(-1, -1, -1, "Error Parsing"))
                return

            if fs_info.info.ftype == pytsk3.TSK_FS_TYPE_FAT12:
                fs_desc = "FAT12 file system"
            elif fs_info.info.ftype == pytsk3.TSK_FS_TYPE_ISO9660_DETECT:
                fs_desc = "ISO file system"
            else:
                fs_desc = "Unknown file system"
            # Botch by populating with file system details
            image_file.__partitions__.append(ImagePart(0, 0, 0, fs_desc))
            return

        # Loop through the partition info found
        logging.info("Got image info for: " + image_file.path)
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
                                 str(part.slot_num) + " for image: " + image_file.path)
                    continue

                logging.info("Adding partition: " + part.desc +
                             " for image: " + image_file.path)
                image_file.__partitions__.append(
                    ImagePart(part.addr, part.slot_num, part.start, part.desc))


class ImagePart(object):
    """Encapsulates a disk image partition."""
    def __init__(self, addr, slot, start, desc):
        self.__addr = addr
        self.__slot = slot
        self.__start = start
        self.__desc = desc

    @property
    def addr(self):
        """Return the partitions address."""
        return self.__addr

    @property
    def slot(self):
        """Return the partitions slot."""
        return self.__slot

    @property
    def start(self):
        """Return the partitions start."""
        return self.__start

    @property
    def desc(self):
        """Return the partitions description."""
        return self.__desc

    def to_part_db_map(self, image_id):
        """Returns a database partition object friendly map."""
        return {
            PartFlds.ADDR: self.addr,
            PartFlds.SLOT: self.slot,
            PartFlds.START: self.start,
            PartFlds.DESC: self.desc,
            PartFlds.IMAGE: image_id
        }


class FileSysEle(object):
    """Class to wrap image methods to handle files and directories."""
    def __init__(self, path, size, details, addr, is_directory, is_deleted):
        self.path = path
        self.name = ntpath.basename(path)
        _, self.extension = os.path.splitext(path)
        self.size = size
        self.details = details
        self.addr = addr
        self.__is_directory = is_directory
        self.is_deleted = is_deleted

    @property
    def is_directory(self):
        """Return true if this is a directory."""
        return self.__is_directory

    @classmethod
    def root_element(cls):
        """Returns a new FileSysEle object initialised as a file system root."""
        details = EleDetails('', 0, 0, 0)
        root_element = cls('/', 0, details, -1, True, False)
        return root_element

    @classmethod
    def from_partition(cls, partition, path):
        """Returns a new file system element instance created using the partition."""
        parent_path, file_name = os.path.split(path)
        if is_root(parent_path, file_name):
            root_ele = cls.root_element()
            return root_ele
        return cls.get_file_from_dir(partition, parent_path, file_name)

    @classmethod
    def get_file_from_dir(cls, partition, parent_path,
                          file_name):
        """Return a file system element created from the passed information."""
        file_sys_info = cls.get_file_system_info(partition.image.path, partition.start,
                                                 partition.image.bps)
        parent_dir = file_sys_info.open_dir(path=parent_path)
        for child_file in parent_dir:
            if (child_file.info.meta != None) and (child_file.info.name.name == file_name):
                logging.debug("Found file: " +
                              child_file.info.name.name + " against " + file_name)
                return cls.from_file_info(parent_path, child_file.info)
        return None

    @classmethod
    def from_file_info(cls, path, info):
        """Creates a new FileSysEle instance from the supplied params"""
        details = EleDetails(info.meta.mode, info.meta.mtime, info.meta.atime,
                             info.meta.ctime)
        ele = cls(path + info.name.name, info.meta.size, details, info.meta.addr,
                  is_dir(info.meta.type), is_ele_deleted(info))
        return ele

    @staticmethod
    def get_file_system_info(image_path, start, block_size):
        """Wrapper method, retrieves the file system info."""
        logging.debug("Getting Image info for:" + image_path +
                      " start:" + str(start) + " size:" + str(block_size))
        image_info = pytsk3.Img_Info(image_path)
        # Open the file system for this image at the extracted
        # start_offset.
        logging.debug("Getting Image Info offset:" + str(start * block_size))
        _fsinfo = pytsk3.FS_Info(image_info, offset=(start * block_size))
        return _fsinfo

    @classmethod
    def list_files(cls, partition, path):
        """List all of the files in a directory."""
        file_list = []
        file_sys_info = cls.get_file_system_info(
            partition.image.path, partition.start, partition.image.bps)
        directory = file_sys_info.open_dir(path=path)
        for listed_file in directory:
            if listed_file.info.meta != None:
                file_list.append(FileSysEle.from_file_info(
                    '/' + path + '/', listed_file.info))
        return file_list

    @classmethod
    def create_temp_copy(cls, partition, fs_ele):
        """Creates a temp file copy of a file from the specified image."""
        generator = cls.payload_generator(partition.image.path, partition.start,
                                          partition.image.bps, fs_ele)
        # Open with a named temp file
        with tempfile.NamedTemporaryFile(delete=False) as temp:
            for data in generator:
                temp.write(data)
                temp.flush()
            # Return an opened temp file
            return temp.name

    @classmethod
    def payload_generator(cls, image_path, start, block_size, fs_ele):
        """Generator used to loop through a file's content."""
        logging.debug("Getting image file information")
        file_sys_info = cls.get_file_system_info(image_path, start, block_size)
        image_file = file_sys_info.open_meta(inode=fs_ele.addr)
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
    def guess_mime_type(cls, file_name):
        """Function to guess the MIME type of a file by filename extension.
        DOCTESTS:
        >>> FileSysEle.guess_mime_type('name.pdf')
        'application/pdf'
        >>> FileSysEle.guess_mime_type('name.docx')
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        >>> FileSysEle.guess_mime_type('name.xls')
        'application/vnd.ms-excel'
        >>> FileSysEle.guess_mime_type('name.txt')
        'text/plain'
        """
        return MimeTypes().guess_type(file_name)[0]

class EleDetails(object):
    """Details of a file system element."""
    def __init__(self, mode, mtime, atime, ctime):
        self.__mode = mode
        self.__mtime = datetime.datetime.fromtimestamp(
            mtime).isoformat() if mtime != 0 else Defaults.NA
        self.__atime = datetime.datetime.fromtimestamp(
            atime).isoformat() if atime != 0 else Defaults.NA
        self.__ctime = datetime.datetime.fromtimestamp(
            ctime).isoformat() if ctime != 0 else Defaults.NA

    @property
    def mode(self):
        """Return the elements mode."""
        return self.__mode

    @property
    def mtime(self):
        """Return the elements modified time."""
        return self.__mtime

    @property
    def atime(self):
        """Return the elements last accessed time."""
        return self.__atime

    @property
    def ctime(self):
        """Return the elements created time."""
        return self.__ctime

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
    """Convenience methood to convert a string to a date."""
    return datetime.datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%S")

def strip_mtime(mtime):
    """Convenience formatter for mtime."""
    return time.strftime("%FT%TZ", time.gmtime(mtime))

def is_ele_deleted(info):
    """Returns true if the info metadata flag is set."""
    return int(info.meta.flags) & 0x01 == 0


def is_candidate(info):
    """Check if this is a candidate for text extraction
    Get just the extension (this is dirty, also gets dotfile names now)
    """
    file_ext = (info.name.name).rsplit('.', 1)
    if len(file_ext) > 1:
        return file_ext[1] in FileExtns.ALLEXT
        #logging.debug("End after split:" + fa[1])
    return False


def is_dir(meta_type):
    """Checks the meta_type from image info to see if the element is a directory
    """
    return meta_type == 2

def is_root(parent, file_to_check):
    """Checks whether a file system element is a root directory."""
    return (parent in PathChars.SEPS) and not file_to_check
