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
import logging
import os

from sqlalchemy.exc import IntegrityError

from .config import LUCENE_ROOT, ENV_CONF_PROFILE
from .disk_utils import ImageDir, ImageFile, FileSysEle
from .model import Image, Partition, FileElement, Group
from .text_indexer import ImageIndexer
from .utilities import check_param_not_none

os.environ[ENV_CONF_PROFILE] = "analyser"

class ImageAnalyser(object):
    """Analyses the contents of disk images."""
    def __init__(self, image, index_dir):
        self.image = image
        self.index_dir = index_dir

    def analyse(self):
        """Analyse all of the files in a disk image, populate the database record,
        and carry out full text indexing if possible / appropriate."""
        logging.info("Analysing image %s", self.image.path)
        with ImageIndexer(self.index_dir) as indexer:
            for partition in self.image.partitions:
                self.analyse_partition(partition, indexer)

    def analyse_partition(self, partition, indexer):
        """Analyse a given partition from a disk image."""
        root_dir = FileSysEle.from_partition(partition, '/')
        self.analyse_directory(partition, root_dir, indexer)

    def analyse_directory(self, partition, directory, indexer):
        """Analyse a particular directory from a partition."""
        logging.debug("Analysing directory %s", directory.path)
        if not directory.is_directory:
            raise ValueError("Argument {} must be a directory path on the image.".format(directory))

        for fs_ele in FileSysEle.list_files(partition, directory.path):
            if fs_ele.name == '.' or fs_ele.name == '..':
                # skip the inodes for current dir and parent
                continue
            if fs_ele.is_directory:
                self.analyse_directory(partition, fs_ele, indexer)
            # Check whether we've seen this path before
            file_element = FileElement.by_partition_and_path(partition,
                                                             os.path.abspath(fs_ele.path))
            if file_element is None:
                self.analyse_file(partition, fs_ele, indexer)

    @classmethod
    def analyse_file(cls, partition, fs_ele, indexer):
        """For a given file system element and partition this method adds the
        file element to the db, and the byte sequence then indexes the file."""
        logging.debug("Analysing file %s", os.path.abspath(fs_ele.path))
        try:
            temp_file = FileSysEle.create_temp_copy(partition, fs_ele)
        except IOError as _:
            logging.exception("IO/Error processing file %s", fs_ele.path)
            return
        byte_sequence, _ = indexer.index_path(temp_file, fs_ele.path)
        file_element = FileElement(os.path.abspath(fs_ele.path), partition, byte_sequence)
        FileElement.add(file_element)
        os.remove(temp_file)


class DbSynch(object):
    """Class that synchs images in a group with the DB record.
    """
    def __init__(self, group, path):
        self.group = group
        self.path = path
        self.__image_dir__ = ImageDir.from_root_dir(self.path)
        self.__not_in_db__ = []
        self.__not_on_disk__ = []
        self.__not_in_group__ = []

    def synch_db(self):
        """Updates the database with images found in the image directory."""
        # Loop through the disk images in the image directory
        for image_file in self.__image_dir__.images:
            # Check to see if the image is in the database
            db_image = Image.by_path(image_file.path)
            if db_image is None:
                logging.info("Adding new image at: %s to database.", image_file.path)
                image = image_file.to_model_image()
                Image.add(image)

                # Add the partitions for the image
                logging.info("Finding partitions for image id: %s, path: %s.",
                             image.id, image_file.path)
                ImageFile.populate_parts(image, image_file)
                for part in image_file.get_partitions():
                    logging.info("Adding partition slot: %d for image id: %s, path: %s.",
                                 part.slot, image.id, image_file.path)
                    try:
                        Partition.add(part)
                    except IntegrityError as _:
                        logging.exception("Duplicate partition detected for" \
                                          "image id: %s, partition slot: %d",
                                          image.id, part.slot)


            db_image = Image.by_path(image_file.path)
            # Now check that the image belongs to this group
            if not self.is_image_in_group(db_image):
                logging.info("Adding image: %s to group %s.", image_file.path, self.group.name)
                self.group.add_image(db_image)

    def images_not_in_goup(self):
        """Checks that images on the disk are in the group."""
        del self.__not_in_group__[:]
        for image in self.__image_dir__.images:
            if not self.is_image_in_group(image.path):
                self.__not_in_group__.append(image)

    def is_image_in_group(self, image):
        """Return true if the image and image_path is in this group."""
        for group_image in self.group.images:
            if group_image.id == image.id:
                return True
        return False

    def images_not_on_disk(self):
        """Checks that images in the database are also on disk.
        Missing images are added to a member list,
        """
        del self.__not_on_disk__[:]
        for image in Image.all():
            if not os.path.isfile(image.path):
                logging.debug("Image: %s is no longer on disk.", image.path)
                self.__not_on_disk__.append(image)

class GroupFileParser(object):
    """Class that parses Group details from config files."""
    def __init__(self, config_path=None):
        self.groups = type('test', (object,), {"GROUPS" : []})()
        if config_path:
            self.parse_config(config_path)

    def parse_config(self, config_path):
        """Parse the group dictionaries from the JSON file."""
        check_param_not_none(config_path, "config_path")
        self.groups = type('test', (object,), {"GROUPS" : []})()
        logging.info("Parsing group file: %s", config_path)
        try:
            with open(config_path, mode='rb') as config_file:
                exec(compile(config_file.read(), config_path, 'exec'),
                     self.groups.__dict__)
        except IOError as _e:
            # if silent and e.errno in (errno.ENOENT, errno.EISDIR):
            #     return False
            _e.strerror = 'Unable to load configuration file (%s)' % _e.strerror
            raise

    def get_groups(self):
        """Return the GROUPS element for iterating."""
        return self.groups.GROUPS

def main():
    """Main method to drive image analyser."""
    # Parse the group config file
    group_conf_path = '/var/www/bcaw/conf/groups.conf'
    try:
        group_parser = GroupFileParser(group_conf_path)
    except IOError as _io_excep:
        logging.exception("IO/Exception reading group config file %s", group_conf_path)
        raise

    # First loop to register groups in DB and allow user to browse
    parsed_groups = group_parser.get_groups()
    for group in parsed_groups:
        # Check to see if the group is in the database, if not add it.
        logging.info("Checking whether group name: %s is in database.", group['name'])
        db_group = Group.by_name(group['name'])
        path = group['path']
        if  db_group is None:
            logging.info("Group name: %s NOT found in database so adding.", group['name'])
            # Add the group to the DB if not already there
            db_group = Group(group['name'], group['description'])
            Group.add(db_group)
        # Synch the group images
        logging.info("Creating synch object for group: %s.", db_group.name)
        db_synch = DbSynch(db_group, path)
        logging.info("Synching group: %s.", db_group.name)
        db_synch.synch_db()

    # Now the heavyweight image analysis loop
    for group in parsed_groups:
        db_group = Group.by_name(group['name'])
        # Loop through the images in the group
        logging.info("Checking group records for %s.", db_group.name)
        for image in db_group.images:
            logging.info("Image %s found in group %s.", image.path, db_group.name)
            if not image.indexed:
                logging.info("Image %s will be indexed now.", image.name)
                analyser = ImageAnalyser(image, LUCENE_ROOT)
                analyser.analyse()
                image.indexed_image()
                logging.info("Finished analysis of image %s.", image.name)
            else:
                logging.info("Image %s was indexed on %s", image.name, image.indexed)


if __name__ == "__main__":
    from .model import init_db # pylint: disable-msg=C0413
    logging.debug("Configured logging.")
    logging.info("Initialising database.")
    init_db()
    main()
