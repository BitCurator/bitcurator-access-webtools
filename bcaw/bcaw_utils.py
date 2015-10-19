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
        volume = pytsk3.Volume_Info(img)
        for part in volume:
            if part.slot_num >= 0:
                try:
                    fs = pytsk3.FS_Info(img, offset=(part.start * 512))
                except:
                    ## print ">> Exception in pytsk3.FS_Info in partition: ", self.num_partitions
                    continue
                self.num_partitions += 1
        return (self.num_partitions)

    def bcawGetPartInfoForImage(self, image_path, image_index):
        img = pytsk3.Img_Info(image_path)
        volume = pytsk3.Volume_Info(img)
        self.partDictList.append([])

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
                print "D: image_path: ", image_path
                print "D: part_addr: ", part.addr
                print "D: part_slot_num: ", part.slot_num
                print "D: part_start_offset: ", part.start
                print "D: part_description: ", part.desc
                # Open the file system for this image at the extracted
                # start_offset.
                try:
                    fs = pytsk3.FS_Info(img, offset=(part.start * 512))
                except:
                    ## print "Exception in pytsk3.FS_Info for partition : ", self.num_partitions
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
                ## print(file_list_root)
    
        image_name = os.path.basename(image_path)
        self.num_partitions_ofimg[image_name] = self.num_partitions
        ## print ("D: Number of Partitions for image = ", image_name, self.num_partitions)
        return (self.num_partitions)

    def bcawGenFileList(self, image_path, image_index, partition_num, root_path):
        print("D1: image_path: {} index: {} part: {} rootpath: {}".format(image_path, image_index, partition_num, root_path))
        img = pytsk3.Img_Info(image_path)
        # Get the start of the partition:
        part_start = self.partDictList[int(image_index)][partition_num-1]['start_offset']

        # Open the file system for this image at the extracted
        # start_offset.
        fs = pytsk3.FS_Info(img, offset=(part_start * 512))

        file_list_root = self.bcawListFiles(fs, root_path, image_index, partition_num)

        return file_list_root, fs
        

    bcawFileInfo = ['name', 'size', 'mode', 'inode', 'p_inode', 'mtime', 'atime', 'ctime', 'isdir', 'deleted', 'name_slug']


    def bcawListFiles(self, fs, path, image_index, partition_num):
        file_list = []
        directory = fs.open_dir(path=path)
        i=0
        for f in directory:
            is_dir = False
            '''
            print("Func:bcawListFiles:root_path:{} size: {} inode: {} \
            par inode: {} mode: {} type: {} ".format(f.info.name.name,\
            f.info.meta.size, f.info.meta.addr, f.info.name.meta_addr,\
            f.info.name.par_addr, f.info.meta.mode, f.info.meta.type))
            '''
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

                # NOTE: A new item "name_slug" is added to those file names which
                # have a space. The space is replaced by %20 and saved as name_slug.
                # This is used later when a file with a "non-None" name_slug shows
                # up at the route. It is recognized as a filename with spaces and
                # using the inode comparison, its real name is extracted before
                # downloading the file.
                name_slug = "None"
                if " " in f.info.name.name:
                    name_slug = f.info.name.name.replace(" ", "%20")

                file_list.append({self.bcawFileInfo[0]:f.info.name.name, \
                              self.bcawFileInfo[1]:f.info.meta.size, \
                              self.bcawFileInfo[2]:f.info.meta.mode, \
                              self.bcawFileInfo[3]:f.info.meta.addr, \
                              self.bcawFileInfo[4]:f.info.name.par_addr, \
                              self.bcawFileInfo[5]:mtime, \
                              self.bcawFileInfo[6]:f.info.meta.atime, \
                              self.bcawFileInfo[7]:f.info.meta.ctime, \
                              self.bcawFileInfo[8]:is_dir, \
                              self.bcawFileInfo[9]:deleted, \
                              self.bcawFileInfo[10]:name_slug })

        ##print("Func:bcawListFiles: Listing Directory for PATH: ", path)
        ##print file_list
        ##print "\n\n"
        return file_list

    def dbGetImageInfoXml(self, image_name):
        if image_name.endswith(".E01") or image_name.endswith(".e01"):
            #ewfinfo_xmlfile = os.getcwd() +"/"+ image_name+".xml"
            ewfinfo_xmlfile = image_name+".xml"
            cmd = "ewfinfo -f dfxml "+image_name+ " > "+ewfinfo_xmlfile
            print("CMD: ", ewfinfo_xmlfile, cmd)
            subprocess.check_output(cmd, shell=True)
            return ewfinfo_xmlfile
        elif image.endswith(".AFF") or image.endswith(".aff"):
            # FIXME: does affinfo create xml output?
            cmd = "affinfo "+image_name
            subprocess.check_output(cmd, shell=True)
            print("Need an E01 file to return xml file")
            return None

    def fixup_dfxmlfile_temp(self, dfxmlfile):
        ## print("D: Fix up the dfxml file: ")
        with open(dfxmlfile) as fin, open("tempfile", "w") as fout:
            for line in fin:
                if not "xmlns" in line:
                    if "dc:type" in line:
                        line = line.replace("dc:type","type")
                    fout.write(line)

        fin.close()
        fout.close()

        cmd = "mv tempfile " + dfxmlfile
        subprocess.check_output(cmd, shell=True)
        print(">> : Updated dfxmlfile ")
        return dfxmlfile

    def fixup_dfxmlfile(self, dfxmlfile):
        ##fin = open(dfxmlfile)
        ##fout = open("tempfile", "w")

        '''
        with open(dfxmlfile) as fin, open("tempfile") as fout:
            for line in fin:
                if not "xmlns" in line:
                    fout.write(line)
        '''
        linenumber = 0
        for line in fileinput.input (dfxmlfile, inplace=1):
            linenumber += 1
            if "xmlns" in line:
                print "",
            if linenumber > 6:
                break

    def dbGetInfoFromDfxml(self, image_name):
        # First generate the dfxml file for the image
        #ewfinfo_xmlfile = os.getcwd() +"/"+ image_name+".xml"
        dfxmlfile = image_name+"_dfxml.xml"
        #cmd = "ewfinfo -f dfxml "+image_name+ " > "+ewfinfo_xmlfile

        '''
        # FIXME: Just for testing: dfxml removed and recreted.
        #if dfxml_dir:
        if os.path.exists(dfxmlfile):
            rmcmd = ['rm', dfxmlfile]
            subprocess.check_output(rmcmd)
        '''


        if not os.path.exists(dfxmlfile):
            printstr = "WARNING!!! DFXML FIle " + dfxmlfile + " does NOT exist. Creating one"
            print (printstr)
            cmd = ['fiwalk', '-b', '-g', '-z', '-X', dfxmlfile, image_name]
            print ("CMD: ", dfxmlfile, cmd)
            subprocess.check_output(cmd)

        # Remove the name space info as the xml parsing won't give proper
        # tags with the name space prefix attached.
        print("D: Fiwalk generated dfxml file. Fixing it up now ")
        #self.fixup_dfxmlfile(dfxmlfile)
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
    ## print("D1: bcawGetPathFromDfxml: in_filename: {}, dfxmlfile: {}".format(in_filename, dfxmlfile))

    try:
        tree = ET.parse( dfxmlfile )
    except IOError, e:
        print "Failure Parsing %s: %s" % (dfxmlfile, e)

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
                            ## print("D2: base_filename: {}, f_name: {}".format(base_filename, f_name)) 
                            if in_filename == base_filename:
                                return f_name

    return None

def bcawGetParentDir(filepath):
    file_name_list = filepath.split('/')
    temp_list = filepath.split("/")
    temp_list = file_name_list[0:(len(temp_list)-1)]
    parent_dir = '/'.join(temp_list)
    return parent_dir
