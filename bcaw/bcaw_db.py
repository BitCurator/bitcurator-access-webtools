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
# This file contains BitCurator Access Webtools database support.
#


from flask import Flask, render_template, url_for, Response
from flask.ext.sqlalchemy import SQLAlchemy

app = Flask(__name__)
db = SQLAlchemy(app)
#app.config.from_pyfile(config.py) 
# FIXME: The above line gives error - so added the following 2 lines for now
#SQLALCHEMY_DATABASE_URI = "postgresql://bcadmin:bcadmin@localhost/DimacImages"
#db_uri = app.config['SQLALCHEMY_DATABASE_URI']
#db_uri = "postgresql://bcadmin:bcadmin@localhost/DimacImages"

import os
import bcaw_utils
import xml.etree.ElementTree as ET

image_list = []
#image_dir = app.config['IMAGEDIR']  # FIXME: This is giving keyerror.
image_dir = "/vagrant/disk-images"

#
# bcawGetXmlInfo: Extracts information from the dfxml file
#
def bcawGetXmlInfo(xmlfile):
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
                    #print("HASH TYPE: ", hash_type)
                    dbrec['md5'] = hash_type 
 
    return dbrec

def dbBrowseImages():
    global image_dir
    image_index = 0

    # Since image_list is declared globally, empty it before populating
    global image_list
    del image_list[:]

    for img in os.listdir(image_dir):
        if img.endswith(".E01") or img.endswith(".AFF"):
            #print "\n IMAGE: ", img
            global image_list
            image_list.append(img)

            # FIXME: Partition info will be added to the metadata info 
            # Till then the following three lines are not necessary.
            dm = bcaw_utils.bcaw()
            image_path = image_dir+'/'+img
            dm.num_partitions = dm.bcawGetNumPartsForImage(image_path, image_index)
            xmlfile = dm.dbGetImageInfoXml(image_path)
            if (xmlfile == None):
                #print("No XML file generated for image info. Returning")
                return
            #print("XML File {} generated for image {}".format(xmlfile, img))

            # Read the XML file and populate the record for this image
            dbrec = bcawGetXmlInfo(xmlfile)

            ## print("D: Adding dbrec session to the DB: ", dbrec)
            dbrec['image_name'] = img

            # Populate the db:
            # Add the created record/session to the DB
            bcawDbSessionAdd(dbrec)

            image_index +=1
        else:
            continue
    db.session.commit()
  
    #print 'D: Image_list: ', image_list

class DimacImages(db.Model):
    __tablename__ = 'bcaw-images'
    image_index = db.Column(db.Integer, primary_key=True)
    image_name = db.Column(db.String(60), unique=True)
    #acq_date = db.Column(db.String(80), unique=True)
    #sys_date = db.Column(db.String(80), unique=True)
    acq_date = db.Column(db.String(80))
    sys_date = db.Column(db.String(80))
    os = db.Column(db.String(20))
    file_format = db.Column(db.String)
    media_type = db.Column(db.String(100))
    is_physical = db.Column(db.String(10))
    bps = db.Column(db.Integer)
    media_size = db.Column(db.String(100))
    #media_size = db.Column(db.String(100), unique=True)
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

def bcawDbSessionAdd(dbrec):
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
   #print(">>> Creating tables ")
   db.drop_all()
   db.create_all()

def bcawdb():
    dbinit()
    dbBrowseImages()

## FIXME: Just for testing - Will be removed
@app.route('/')
def index(image_name = None):
    '''
    # Hardcode the image for now: FIXME
    image_name = "charlie-work-usb-2009-12-11.E01"
    #image = DimacImages.query.filter_by(image_name=image_name).first()
    print("Querying the DB ...")
    #image = bcdb.query.filter_by(image_name=image_name).first()
    image = bcdb.query.filter_by(image_name=image_name).first()
    print("img", image.acq_date)
    return render_template("db_temp.html", image=image)
    '''
if __name__=="__main__":
    db = SQLAlchemy(app)
    dbinit()
    dbBrowseImages()
    app.run(debug=True, host="0.0.0.0", port=8888)
    
