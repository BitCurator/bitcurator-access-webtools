#!/usr/bin/python
# coding=UTF-8
#
# DIMAC (Disk Image Access for the Web)
# Copyright (C) 2014
# All rights reserved.
#
# This code is distributed under the terms of the GNU General Public
# License, Version 3. See the text file "COPYING" for further details
# about the terms of this license.
#
# Utilities for the DIMAC application

import pytsk3
import os, sys, string, time, re
import subprocess

#FIXME: Note: This file is created to be the common utils file. A few 
# routines are moved here from image_browse.py file, but are also retained
# in that file for now, because image_browse part is not yet tested with
# this file. Eventually those routines will go away and the routines from 
# this file will be called by both db and browse files.

class dimac:
    num_partitions = 0
    part_array = ["image_path", "addr", "slot_num", "start_offset", "desc"]
    partDictList = []
    num_partitions_ofimg = dict()

    def dimacGetNumPartsForImage(self, image_path, image_index):
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

    def dimacGetPartInfoForImage(self, image_path, image_index):
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
                file_list_root = self.dimacListFiles(fs, "/", image_index, part.slot_num)
                ## print(file_list_root)
    
        image_name = os.path.basename(image_path)
        self.num_partitions_ofimg[image_name] = self.num_partitions
        ## print ("D: Number of Partitions for image = ", image_name, self.num_partitions)
        return (self.num_partitions)

    def dimacGenFileList(self, image_path, image_index, partition_num, root_path):
        img = pytsk3.Img_Info(image_path)
        # Get the start of the partition:
        part_start = self.partDictList[int(image_index)][partition_num-1]['start_offset']

        # Open the file system for this image at the extracted
        # start_offset.
        fs = pytsk3.FS_Info(img, offset=(part_start * 512))

        file_list_root = self.dimacListFiles(fs, root_path, image_index, partition_num)

        return file_list_root, fs
        

    dimacFileInfo = ['name', 'size', 'mode', 'inode', 'p_inode', 'mtime', 'atime', 'ctime', 'isdir', 'deleted']


    def dimacListFiles(self, fs, path, image_index, partition_num):
        file_list = []
        directory = fs.open_dir(path=path)
        i=0
        for f in directory:
            is_dir = False
            '''
            print("Func:dimacListFiles:root_path:{} size: {} inode: {} \
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

                file_list.append({self.dimacFileInfo[0]:f.info.name.name, \
                              self.dimacFileInfo[1]:f.info.meta.size, \
                              self.dimacFileInfo[2]:f.info.meta.mode, \
                              self.dimacFileInfo[3]:f.info.meta.addr, \
                              self.dimacFileInfo[4]:f.info.name.par_addr, \
                              self.dimacFileInfo[5]:mtime, \
                              self.dimacFileInfo[6]:f.info.meta.atime, \
                              self.dimacFileInfo[7]:f.info.meta.ctime, \
                              self.dimacFileInfo[8]:is_dir, \
                              self.dimacFileInfo[9]:deleted })

        ##print("Func:dimacListFiles: Listing Directory for PATH: ", path)
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
        
