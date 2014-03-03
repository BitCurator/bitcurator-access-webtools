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
# This is a python script to populate the database

from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy

app = Flask(__name__)
#app.config.from_pyfile(config.py) 
# FIXME: The above line gives error - so added the following 2 lines for now
SQLALCHEMY_DATABASE_URI = "postgresql://bcadmin:bcadmin@localhost/bcdb"
#db_uri = app.config['SQLALCHEMY_DATABASE_URI']
db_uri = "postgresql://bcadmin:bcadmin@localhost/bcdb"
db = SQLAlchemy(app)

import os
import dimac_utils
import xml.etree.ElementTree as ET

image_list = []
#image_dir = app.config['IMAGEDIR']  # FIXME
image_dir = "/home/bcadmin/disk_images"

'''
dbrec = ['image_name', 'acq_date', 'sys_date', 'os', 'file_format', 
         'media_type', 'is_physical', 'bps', 'media_size', 'md5']
'''

num_images = 0

def dimacGetXmlInfo(xmlfile):
    result = ""
    try:
        tree = ET.parse( xmlfile )
    except IOError, e:
        print "Failure Parsing %s: %s" % (xmlfile, e)

    dbrec = dict()
    root = tree.getroot() # root node
    for child in root:
        if ( child.tag == 'ewfinfo' ):
            ewfinfo = child
            for echild in ewfinfo:
                if (echild.tag == 'acquiry_information'):
                    acqinfo = echild 
                    for acq_child in acqinfo:
                        if (acq_child.tag == 'acquisition_date'):
                            dbrec['acq_date'] = acq_child.text
                        elif (acq_child.tag == 'system_date'):
                            dbrec['sys_date'] = acq_child.text
                        elif (acq_child.tag == 'acquisition_system'):
                            dbrec['os'] = acq_child.text
            
                elif (echild.tag == 'ewf_information'):
                    ewf_info = echild 
                    for ewfi_child in ewf_info:
                        if (ewfi_child.tag == 'file_format'):
                            dbrec['file_format'] = ewfi_child.text
                elif (echild.tag == 'media_information'):
                    media_info = echild
                    for minfo_child in media_info:
                        if (minfo_child.tag == 'media_type'):
                            dbrec['media_type'] = minfo_child.text
                        elif (minfo_child.tag == 'is_physical'):
                            dbrec['is_physical'] = minfo_child.text
                        elif (minfo_child.tag == 'bytes_per_sector'):
                            dbrec['bps'] = minfo_child.text
                        elif (minfo_child.tag == 'media_size'):
                            dbrec['media_size'] = minfo_child.text
                elif (echild.tag == 'hashdigest'):
                    hash_type = echild.text  ## FIXME
                    print("HASH TYPE: ", hash_type)
                    dbrec['md5'] = hash_type 
 
            '''
            getAcquiryInfo(ewfinfo)
            getEwfInfo(ewfinfo)
            getMediaInfo(ewfinfo)
            '''
    return dbrec

def dbBrowseImages():
    global image_dir
    image_index = 0

    # Since image_list is declared globally, empty it before populating
    global image_list
    del image_list[:]

    for img in os.listdir(image_dir):
        if img.endswith(".E01") or img.endswith(".AFF"):
            print "IMAGE: ", img
            global image_list
            image_list.append(img)

            # FIXME: Partition info will be added to the metadata info 
            # Till then the following three lines are not necessary.
            dm = dimac_utils.dimac()
            image_path = image_dir+'/'+img
            dm.num_partitions = dm.dimacGetPartInfoForImage(image_path, image_index)
            xmlfile = dm.dbGetImageInfoXml(image_path)
            if (xmlfile == None):
                print("No XML file generated for image info. Returning")
                return
            print("XML File {} generated for image {}".format(xmlfile, img))

            # Read the XML file and populate the record for this image
            dbrec = dimacGetXmlInfo(xmlfile)

            print("Adding dbrec session to the DB: ", dbrec)
            dbrec['image_name'] = img

            # Populate the db:
            # Add the created record/session to the DB
            dimacDbSessionAdd(dbrec)

            image_index +=1
        else:
            continue
  
    print 'D: Image_list: ', image_list
    global num_images
    num_images = len(image_list)

class DimacImages(db.Model):
    image_index = db.Column(db.Integer, primary_key=True)
    image_name = db.Column(db.String(60), unique=True)
    acq_date = db.Column(db.DateTime)
    sys_date = db.Column(db.DateTime)
    os = db.Column(db.String(20))
    file_format = db.Column(db.String)
    media_type = db.Column(db.String(100), unique=True)
    is_physical = db.Column(db.String(10), unique=True)
    bps = db.Column(db.Integer, unique=True)
    media_size = db.Column(db.String(100), unique=True)
    md5 = db.Column(db.String(100))

    def __init__(self, image_name = None, acq_date = None, sys_date = None,
os = None, file_format = None, media_type = None, is_physical = None, 
bps = None, media_size = None, md5 = None):
        self.image_name = image_name
        self.acq_date = acq_date
        self.sys_date = sys_date
        self.os = os
        self.file_format = file_format
        self.media_type = media_type
        self.is_physical = is_physical
        self.bps = bps
        self.media_size = media_size
        self.md5 = md5


def dimacDbSessionAdd(dbrec):
   db.session.add(DimacImages(image_name=dbrec['image_name'], 
                         acq_date=dbrec['acq_date'],
                         sys_date=dbrec['sys_date'],
                         os=dbrec['os'], file_format=dbrec['file_format'],
                         media_type=dbrec['media_type'],
                         is_physical=dbrec['is_physical'],
                         bps = dbrec['bps'],
                         media_size = dbrec['media_size'],
                         md5 = dbrec['md5'])) 
    
def dbinit(): 
   db.drop_all()
   db.create_all()

@app.route('/')
def index(image_name = None):
    image = DimacImages.query.filter_by(image_name=image_name).first()
    return render_template("db_temp.html", image=image)
        

if __name__=="__main__":
    dbinit()
    dbBrowseImages()
    app.run(debug=True, host="0.0.0.0", port=8888)
    
