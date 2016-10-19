#!/usr/bin/python
# coding=UTF-8
#
# BitCurator Access Webtools (Disk Image Access for the Web)
# Copyright (C) 2014
# All rights reserved.
#
# This code is distributed under the terms of the GNU General Public
# License, Version 3. See the text file "COPYING" for further details
# about the terms of this license.
#
# Utilities for the BitCurator Access Webtools application

# For is_text routine
from __future__ import division
import string

import pytsk3
import os, sys, string, time, re
import logging
import subprocess
import fileinput
import xml.etree.ElementTree as ET

#FIXME: Note: This file is created to be the common utils file. A few
# routines are moved here from image_browse.py file, but are also retained
# in that file for now, because image_browse part is not yet tested with
# this file. Eventually those routines will go away and the routines from
# this file will be called by both db and browse files.

class bcaw:
    num_partitions = 0
    part_array = ["image_path", "addr", "slot_num", "start_offset", "desc"]
    partDictList = []
    num_partitions_ofimg = dict()

    def bcawGetNumPartsForImage(self, image_path, image_index):
        img = pytsk3.Img_Info(image_path)

        # pytsk3.Volume_Info works only with file systems which have partition
        # defined. For file systems like FAT12, with no partition info, we need
        # to handle in an exception.
        try:
            volume = pytsk3.Volume_Info(img)
        except:
            ## print "bcawGetNumPartsForImage: Volume Info failed. Could be FAT12 "
            self.num_partitions = 1
            return (self.num_partitions)

        for part in volume:
            if part.slot_num >= 0:
                try:
                    fs = pytsk3.FS_Info(img, offset=(part.start * 512))
                except:
                    continue
                self.num_partitions += 1
        return (self.num_partitions)

    def bcawGetPartInfoForImage(self, image_path, image_index):
        img = pytsk3.Img_Info(image_path)
        is_partition_info = False

        # pytsk3.Volume_Info works only with file systems which have partition
        # defined. For file systems like FAT12, with no partition info, we need
        # to handle in an exception.
        try:
            volume = pytsk3.Volume_Info(img)
            is_partition_info = True
        except:
            self.num_partitions = 1
            is_partition_info = False
            fs = pytsk3.FS_Info(img, offset=0)

            ## print "D: File System Type Detected ", fs.info.ftype
            if fs.info.ftype == pytsk3.TSK_FS_TYPE_FAT12:
                fs_desc = "FAT12 file system"
            elif fs.info.ftype == pytsk3.TSK_FS_TYPE_ISO9660_DETECT:
                fs_desc = "ISO file system"
            else:
                fs_desc = "Unknown file system"

            self.partDictList.append([])
            # First level files and directories off the root
            # returns file_list for the root directory
            file_list_root = self.bcawListFiles(fs, "/", image_index, 0)
            image_name = os.path.basename(image_path)
            self.num_partitions_ofimg[image_name] = self.num_partitions

            # Populate the partDictList for the image.
            self.partDictList[image_index].append({self.part_array[0]:image_path, \
                                     self.part_array[1]:0, \
                                     self.part_array[2]:0, \
                                     self.part_array[3]:0, \
                                     self.part_array[4]:fs_desc })
            return self.num_partitions

        # For images with partition_info, we continue here.
        self.partDictList.append([])

        self.num_partitions = 0
        for part in volume:
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
                    fs = pytsk3.FS_Info(img, offset=(part.start * 512))
                except:
                    continue
                self.partDictList[image_index].append({self.part_array[0]:image_path, \
                                     self.part_array[1]:part.addr, \
                                     self.part_array[2]:part.slot_num, \
                                     self.part_array[3]:part.start, \
                                     self.part_array[4]:part.desc })

                self.num_partitions += 1

                fs = pytsk3.FS_Info(img, offset=(part.start * 512))

                # First level files and directories off the root
                # returns file_list for the root directory
                file_list_root = self.bcawListFiles(fs, "/", image_index, part.slot_num)

        image_name = os.path.basename(image_path)
        self.num_partitions_ofimg[image_name] = self.num_partitions
        return (self.num_partitions)

    def bcawGenFileList(self, image_path, image_index, partition_num, root_path):
        logging.debug('D1: image_path: %s index: %s part: %s root_path: %s ', image_path, image_index, partition_num, root_path)
        img = pytsk3.Img_Info(image_path)
        # Get the start of the partition:
        part_start = self.partDictList[int(image_index)][partition_num-1]['start_offset']

        # Open the file system for this image at the extracted
        # start_offset.
        fs = pytsk3.FS_Info(img, offset=(part_start * 512))

        file_list_root = self.bcawListFiles(fs, root_path, image_index, partition_num)

        return file_list_root, fs


    bcawFileInfo = ['name', 'size', 'mode', 'inode', 'p_inode', 'mtime', 'atime', 'ctime', 'isdir', 'deleted']


    def bcawListFiles(self, fs, path, image_index, partition_num):
        file_list = []
        try:
           directory = fs.open_dir(path=path)
        except:
           print "Error in opening file path {} ".format(path)
           return None

        i=0
        for f in directory:
            is_dir = False
            # Some files may not have the metadta information. So
            # access it only if it exists.
            if f.info.meta != None:
                if f.info.meta.type == 2:
                    is_dir = True

                # Since we are displaying the modified time for the file,
                # Convert the mtime to isoformat to be passed in file_list.
                ## d = date.fromtimestamp(f.info.meta.mtime)
                ## mtime = d.isoformat()
                mtime = time.strftime("%FT%TZ",time.gmtime(f.info.meta.mtime))


                if (int(f.info.meta.flags) & 0x01 == 0):
                    deleted = "Yes"
                else:
                    deleted = "No"

                file_list.append({self.bcawFileInfo[0]:f.info.name.name, \
                              self.bcawFileInfo[1]:f.info.meta.size, \
                              self.bcawFileInfo[2]:f.info.meta.mode, \
                              self.bcawFileInfo[3]:f.info.meta.addr, \
                              self.bcawFileInfo[4]:f.info.name.par_addr, \
                              self.bcawFileInfo[5]:mtime, \
                              self.bcawFileInfo[6]:f.info.meta.atime, \
                              self.bcawFileInfo[7]:f.info.meta.ctime, \
                              self.bcawFileInfo[8]:is_dir, \
                              self.bcawFileInfo[9]:deleted })

        return file_list

    def dbGetImageInfoXml(self, image_name):
        if image_name.endswith(".E01") or image_name.endswith(".e01"):
            ewfinfo_xmlfile = image_name+".xml"
            cmd = "ewfinfo -f dfxml "+image_name+ " > "+ewfinfo_xmlfile
            logging.debug('CMD xmlfile: %s', ewfinfo_xmlfile)
            logging.debug('CMD: %s', cmd)
            if not os.path.exists(ewfinfo_xmlfile):
                c=subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            return ewfinfo_xmlfile
        elif image_name.endswith(".AFF") or image_name.endswith(".aff"):
            # FIXME: does affinfo create xml output?
            cmd = "affinfo "+image_name
            subprocess.check_output(cmd, shell=True)
            logging.debug('Need an E01 file to return xml file')
            return None

    def fixup_dfxmlfile_temp(self, dfxmlfile):
        with open(dfxmlfile) as fin, open("/tmp/tempfile", "w") as fout:
            for line in fin:
                if not "xmlns" in line:
                    if "dc:type" in line:
                        line = line.replace("dc:type","type")
                    fout.write(line)

        fin.close()
        fout.close()

        cmd = "mv /tmp/tempfile " + dfxmlfile
        subprocess.check_output(cmd, shell=True)
        return dfxmlfile

    def fixup_dfxmlfile(self, dfxmlfile):
        linenumber = 0
        for line in fileinput.input (dfxmlfile, inplace=1):
            linenumber += 1
            if "xmlns" in line:
                logging.debug('Why is this here??? ')
            if linenumber > 6:
                break

    def dbGetInfoFromDfxml(self, image_name):
        # First generate the dfxml file for the image
        dfxmlfile = image_name+"_dfxml.xml"


        if not os.path.exists(dfxmlfile):
            printstr = "WARNING!!! DFXML FIle " + dfxmlfile + " does NOT exist. Creating one"
            logging.warning('Warning: %s ', printstr)
            cmd = ['fiwalk', '-b', '-g', '-z', '-X', dfxmlfile, image_name]
            logging.debug('CMD: %s ', cmd)
            subprocess.check_output(cmd)

        # Remove the name space info as the xml parsing won't give proper
        # tags with the name space prefix attached.
        logging.debug('D: Fiwalk generated dfxml file. Fixing it up now ')
        dfxmlfile = self.fixup_dfxmlfile_temp(dfxmlfile)

        return dfxmlfile

# Routine to detect text files: Got from
# http://stackoverflow.com/questions/1446549/how-to-identify-binary-and-text-files-using-python

def istext(filename):
    s=open(filename).read(512)
    text_characters = "".join(map(chr, range(32, 127)) + list("\n\r\t\b"))
    _null_trans = string.maketrans("", "")
    if not s:
        # Empty files are considered text
        return True
    if "\0" in s:
        # Files with null bytes are likely binary
        return False
    # Get the non-text characters (maps a character to itself then
    # use the 'remove' option to get rid of the text characters.)
    t = s.translate(_null_trans, text_characters)
    # If more than 30% non-text characters, then
    # this is considered a binary file
    if float(len(t))/float(len(s)) > 0.30:
        return False
    return True

def bcawGetPathFromDfxml(in_filename, dfxmlfile):
    """ In order to get the complete path of each file being indexed, we use'
        the information from the dfxml file. This routine looks for the given file
        in the given dfxml file and returns the <filename> info, whic happens
        to be the complete path.
        NOTE: In case this process is contributing significantly
        to the indexing time, we need to find a better way to get this info.
    """
    try:
        tree = ET.parse( dfxmlfile )
    except IOError, e:
        logging.error('Failure parsing DFXML file %s ', e)

    root = tree.getroot() # root node
    for child in root:
        if child.tag == "volume":
            volume = child
            for vchild in volume:
                if vchild.tag == "fileobject":
                    fileobject = vchild
                    for fo_child in fileobject:
                        if fo_child.tag == 'filename':
                            f_name = fo_child.text
                            # if this is the filename, return the path.
                            # "fielname" has the complete path in the DFXML file.
                            # Extract just the fiename to compare with
                            base_filename = os.path.basename(f_name)
                            if in_filename == base_filename:
                                return f_name

    return None

def bcawGetParentDir(filepath):
    file_name_list = filepath.split('/')
    temp_list = filepath.split("/")
    temp_list = file_name_list[0:(len(temp_list)-1)]
    parent_dir = '/'.join(temp_list)
    return parent_dir

# list of image types supporting system metadata
bcaw_sysmeta_supported_list = ['.E01', '.e01', '.aff', '.AFF']

# list of raw image types
bcaw_raw_image_list = ['.raw', '.dd', '.iso']

bcaw_supported_imgtype_list = bcaw_sysmeta_supported_list + bcaw_raw_image_list;

def bcaw_is_imgtype_supported(image):
    imgname, img_extension = os.path.splitext(image)
    if img_extension in bcaw_supported_imgtype_list:
        return True
    else:
        logging.debug("Image type %s not supported", img_extension)
        return False

def bcaw_is_sysmeta_supported(image):
    imgname, img_extension = os.path.splitext(image)
    if img_extension in bcaw_sysmeta_supported_list:
        return True
    else:
        logging.debug("Image type %s doesnot have system metadata", img_extension)
        return False

def is_image_raw(image):
    imgname, img_extension = os.path.splitext(image)
    if img_extension in bcaw_raw_image_list:
        return True
    return False
