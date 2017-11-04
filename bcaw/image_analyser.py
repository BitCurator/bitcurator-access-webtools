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
"""Service that analyses new image groups for the BitCurator app."""
import json
import logging
import os

from .config import LUCENE_ROOT
from .disk_utils import ImageDir, ImageFile, FileSysEle
from .model import Image, Partition, FileElement, Group
from .text_indexer import ImageIndexer

class ImageAnalyser(object):
    """Analyses the contents of disk images."""
    def __init__(self, image, index_dir):
        self.image = image
        self.index_dir = index_dir

    def analyse(self):
        """Analyse all of the files in a disk image, populate the database record,
        and carry out full text indexing if possible / appropriate."""
        print "Analysing image {}".format(self.image.path)
        with ImageIndexer(self.index_dir) as indexer:
            for partition in self.image.partitions:
                self.analyse_partition(partition, indexer)

    def analyse_partition(self, partition, indexer):
        """Analyse a given partition from a disk image."""
        root_dir = FileSysEle.from_partition(partition, '/')
        self.analyse_directory(partition, root_dir, indexer)

    def analyse_directory(self, partition, directory, indexer):
        """Analyse a particular directory from a partition."""
        print "Analysing directory {}".format(directory.path)
        if not directory.is_directory:
            raise ValueError("Argument {} must be a directory path on the image.".format(directory))

        for fs_ele in FileSysEle.list_files(partition, directory.path):
            if fs_ele.name == '.' or fs_ele.name == '..':
                # skip the inodes for current dir and parent
                continue
            if fs_ele.is_directory:
                self.analyse_directory(partition, fs_ele, indexer)
            # Check whether we've seen this path before
            file_element = FileElement.by_partition_and_path(partition, os.path.abspath(fs_ele.path))
            if file_element is None:
                self.analyse_file(partition, fs_ele, indexer)

    @classmethod
    def analyse_file(cls, partition, fs_ele, indexer):
        """For a given file system element and partition this method adds the
        file element to the db, and the byte sequence then indexes the file."""
        print "Analysing file {}".format(os.path.abspath(fs_ele.path))
        try:
            temp_file = FileSysEle.create_temp_copy(partition, fs_ele)
        except IOError as _:
            print "IO/Error processing file {}".format(fs_ele.path)
            return
        byte_sequence, _ = indexer.index_path(temp_file)
        file_element = FileElement(os.path.abspath(fs_ele.path), partition, byte_sequence)
        FileElement.add(file_element)
        os.remove(temp_file)


class DbSynch(object):
    """Class that synchs images in a group with the DB record.
    """
    def __init__(self, group):
        self.group = group
        self.__image_dir__ = ImageDir.from_root_dir(self.group.path)
        self.__not_in_db__ = []
        self.__not_on_disk__ = []

    def is_synch_db(self):
        """Returns true if the database needs resynching with file system."""
        # First synch the image directory with the file system
        self.__image_dir__ = ImageDir.from_root_dir(self.group.path)
        return len(self.group.get_images()) != self.__image_dir__.count()

    def synch_db(self):
        """Updates the database with images found in the image directory."""
        if not self.is_synch_db():
            return
        # Deal with images not in the database first
        self.images_not_in_db()
        for image_file in self.__not_in_db__:
            logging.info("Adding image: " + image_file.path + " to database.")
            image = image_file.to_model_image(self.group)
            Image.add(image)
            ImageFile.populate_parts(image, image_file)
            for part in image_file.get_partitions():
                Partition.add(part)

        for image in self.__not_on_disk__:
            logging.warn("Image: " + image.path + " appears to have been deleted from disk.")

    def images_not_in_db(self):
        """Checks that images on the disk are also on database.
        Missing images are added to a member list,
        """
        del self.__not_in_db__[:]
        for image in self.__image_dir__.images:
            db_image = Image.by_path(image.path)
            if db_image is None:
                logging.debug("Image: " + image.path + " not in database.")
                self.__not_in_db__.append(image)

    def images_not_on_disk(self):
        """Checks that images in the database are also on disk.
        Missing images are added to a member list,
        """
        del self.__not_on_disk__[:]
        for image in Image.all():
            if not os.path.isfile(image.path):
                logging.debug("Image: " + image.path + " is no longer on disk.")
                self.__not_on_disk__.append(image)

def main():
    """Main method to drive image analyser."""
    # Parse the group dictionaries from the JSON file
    # groups = json.loads(GROUPS)
    # Loop through the groups in the list
    groups = type('test', (object,), {"GROUPS" : []})()
    try:
        with open('/var/www/bcaw/conf/groups.conf', mode='rb') as config_file:
            exec(compile(config_file.read(), '/var/www/bcaw/conf/groups.conf', 'exec'),
                 groups.__dict__)
    except IOError as _e:
        # if silent and e.errno in (errno.ENOENT, errno.EISDIR):
        #     return False
        _e.strerror = 'Unable to load configuration file (%s)' % _e.strerror
        raise

    for group in groups.GROUPS:
        # Check to see if the group is in the database, if not add it.
        db_coll = Group.by_path(group['path'])
        if  db_coll is None:
            db_coll = Group(group['path'], group['name'],
                            group['description'])
            Group.add(db_coll)
        db_synch = DbSynch(db_coll)
        db_synch.synch_db()
        for image in db_coll.images:
            analyser = ImageAnalyser(image, LUCENE_ROOT)
            analyser.analyse()

if __name__ == "__main__":
    from .model import init_db # pylint: disable-msg=C0413
    logging.debug("Configured logging.")
    logging.info("Initialising database.")
    init_db()
    main()
