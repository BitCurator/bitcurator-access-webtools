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
# This file contains the main BitCurator Access Webtools application.
#

from flask import Flask, render_template, url_for, Response, stream_with_context, request, flash, session, redirect
from bcaw_forms import ContactForm, SignupForm, SigninForm, QueryForm, adminForm, buildForm

import pytsk3
import os, sys, string, time, re
from mimetypes import MimeTypes
from datetime import date
from bcaw_utils import bcaw
import bcaw_utils
import lucene

from bcaw import app
import bcaw_db
import bcaw_index
from sqlalchemy import *
from bcaw_userlogin_db import db_login, User, dbinit
###from runserver import db_login
from werkzeug.routing import BaseConverter

import subprocess
from subprocess import Popen,PIPE

'''
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relation, sessionmaker
'''
'''
# searchable is commented outfor now
import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy_searchable import make_searchable
from sqlalchemy_utils.types import TSVectorType
from sqlalchemy.orm import relation, sessionmaker

from sqlalchemy_searchable import search


Base = declarative_base()

make_searchable()
'''

image_list = []
file_list_root = []
checked_list_dict = dict()

'''
NOTE: This function is a copy of bcawBroseImages, but with some changes (like
not initializing DB). Due to some issue with calling this routine from home(), 
and other route routines, the same code is inlined in those routines for now.
It needs to be changed by calling this routine instead.  

def bcawBrowse(db_init = True):
    global image_dir
    image_index = 0

    # Two lists are maintained: image_list: List of image names, 
    # image_db_list: List of the db_elements of all images. Each element is
    # a db-structure.
    # Since lists are declared globally, empty them before populating
    global image_list
    del image_list[:]
    global image_db_list
    del image_db_list [:]

    # Create the DB. FIXME: This needs to be called from runserver.py 
    # before calling run. That seems to have some issues. So calling from
    # here for now. Need to fix it.
    if db_init == True:
        session1 = bcaw_db.bcawdb()

    for img in os.listdir(image_dir):
        if img.endswith(".E01") or img.endswith(".AFF"):
            ## print img
            global image_list

            dm = bcaw()
            image_path = image_dir+'/'+img
            dm.num_partitions = dm.bcawGetPartInfoForImage(image_path, image_index)
            image_list.append(img, dm.num_partitions)

            idb = bcaw_db.BcawImages.query.filter_by(image_name=img).first()
            image_db_list.append(idb)
            ## print("D: IDB: image_index:{}, image_name:{}, acq_date:{}, md5: {}".format(image_index, idb.image_name, idb.acq_date, idb.md5)) 
            image_index +=1
        else:
            continue

    # Render the template for main page.
    # print 'D: Image_list: ', image_list
    global num_images
    num_images = len(image_list)

    user = "Sign In"
    signup_out = "Sign Up"
    if 'email' in session:
      user = session['email']
      signup_out = "Sign Out"

    qform = QueryForm()

    return render_template('fl_temp_ext.html', image_list=image_list, np=dm.num_partitions, image_db_list=image_db_list, user=user, signup_out = signup_out, form=qform)

'''

# image_matrix is a global list of dictioaries, bcaw_imginfo, one per image.
image_matrix = []
bcaw_imginfo = ['img_index', 'img_name', 'img_db_exists', 'dfxml_db_exists', 'index_exists']

def bcawPopulateImgInfoTable(image_index, img, imgdb_flag, dfxmldb_flag, index_flag):
    """ For the given image (img), this routine updates the corresponding
        fields of bcaw_imginfo within the list image_matrix.
        FIXME: Yet to add code to update index flag.
    """
    ## print "[D]: bcawPopulateImgInfoTable: index, img: ", image_index, img
    if img:
        img_db_exists = False
        dfxml_db_exists = False

        # Query the DB to see if tables exist for the given image.
        if bcaw_db.dbu_does_table_exist_for_img(img, "bcaw_images"):
            img_db_exists = True
        if bcaw_db.dbu_does_table_exist_for_img(img, "bcaw_dfxmlinfo"):
            dfxml_db_exists = True

        # Add the querried info to the matrix.
        image_matrix.append({bcaw_imginfo[0]:image_index, bcaw_imginfo[1]:img, bcaw_imginfo[2]:img_db_exists, bcaw_imginfo[3]:dfxml_db_exists, bcaw_imginfo[4]:0})

    ''' FIXME: REMOVE AFTER TESTING as this is not used
    if imgdb_flag:
        image_matrix.append({bcaw_imginfo[0]:image_index, bcaw_imginfo[1]:img})
    '''
    ## print "[D] bcawPopulateImgInfoTable: ", image_matrix

#FIXME: The following line should be called in __init__.py once.
# Since that is not being recognized here, app.config.from_object is
# added here. This needs to be fixed.
app.config.from_object('bcaw_default_settings')
image_dir = app.config['IMAGEDIR']
dirFilesToIndex = app.config['FILES_TO_INDEX_DIR']
indexDir = app.config['INDEX_DIR']
num_images = 0
image_db_list = []

@app.route("/")

def bcawBrowseImages(db_init=True):
    global image_dir
    image_index = 0

    # Two lists are maintained: image_list: List of image names, 
    # image_db_list: List of the db_elements of all images. Each element is
    # a db-structure.
    # Since image_list is declared globally, empty it before populating
    global image_list
    del image_list[:]
    global image_db_list
    del image_db_list [:]
    global partition_in

    partition_in = dict()

    # Create the DB. FIXME: This needs to be called from runserver.py 
    # before calling run. That seems to have some issues. So calling from
    # here for now. Need to fix it.
    if db_init == True:
        session1 = bcaw_db.bcawdb()

    for img in os.listdir(image_dir):
        if img.endswith(".E01") or img.endswith(".AFF"):
            ## print img
            ### global image_list

            dm = bcaw()
            image_path = image_dir+'/'+img
            dm.num_partitions = dm.bcawGetPartInfoForImage(image_path, image_index)
            image_list.append(img)
            partition_in[img] = dm.num_partitions

            idb = bcaw_db.BcawImages.query.filter_by(image_name=img).first()
            image_db_list.append(idb)
 
            ## print("D: IDB: image_index:{}, image_name:{}, acq_date:{}, md5: {}".format(image_index, idb.image_name, idb.acq_date, idb.md5)) 

            # Populate the image info table with this image name and index
            if bcawIsImgInMatrix(img):
                print ">> [D]Not populating the image matrix as it already exists for image", img
            else:
                bcawPopulateImgInfoTable(image_index, img, 0, 0, 0)
                image_index +=1
        else:
            continue

    ### global partition_in

    # Render the template for main page.
    # print 'D: Image_list: ', image_list
    global num_images
    num_images = len(image_list)

    user = "Sign In"
    signup_out = "Sign Up"
    if 'email' in session:
      user = session['email']
      signup_out = "Sign Out"

    qform = QueryForm()

    return render_template('fl_temp_ext.html', image_list=image_list, np=dm.num_partitions, image_db_list=image_db_list, user=user, signup_out = signup_out, form=qform)

def bcawDnldSingleFile(file_item, fs, filepath, index_dir):
    """ While indexing we download every file in the image, index it and remove. This
        routine does exactly that - gets the inode of the file_item, calls the
        pytsk3 APs (open_meta, info.meta, read_random) to get the handle for that
        file, extract the size and read the data into a buffer.
        The buffer is copied into a file, which rsides in the same path as it does
        wihtin the disk image.
    """
    ## print(">> D1: Downloading File: {}, filepath: {} ".format(file_item['name'], filepath))

    f = fs.open_meta(inode=file_item['inode'])

    # Read data and store it in a string
    offset = 0
    size = f.info.meta.size
    BUFF_SIZE = 1024 * 1024

    total_data = ""
    while offset < size:
        available_to_read = min(BUFF_SIZE, size - offset)
        data = f.read_random(offset, available_to_read)
        if not data:
            # print("Done with reading")
            break

        offset += len(data)
        total_data = total_data+data
        ## print("D2: Length OF TOTAL DATA: ", len(total_data))

    ## print("D2: Dumping the contents to filepath ", filepath)

    with open(filepath, "w") as text_file:
        text_file.write(total_data)

    ## print ("D2: Time to index the file ", filepath)
    basepath = os.path.dirname(filepath)
    bcaw_index.IndexFiles(basepath, index_dir)

    ## print("D2: Done Indexing the file. Time to delete it ", filepath)

    rmcmd = "rm " + '"' + filepath + '"'
    subprocess.check_output(rmcmd, shell=True, stderr=subprocess.STDOUT)
    ## print("D2:: Removed file ", filepath)

    if filepath.endswith('.pdf'):
        filepath_txt = filepath.replace('.pdf', '.txt')
        rmcmd_1 = "rm " + '"' + filepath_txt + '"'
        if os.path.exists(filepath_txt):
            subprocess.check_output(rmcmd_1, shell=True, stderr=subprocess.STDOUT)

def bcawDnldRepo(img, root_dir_list, fs, image_index, partnum, image_path, root_path):
    """This routine is used to download the indexable files of the Repository
    """
    ## print("D: bcawDnldRepo: Root={} len={} ".format(root_path, len(root_dir_list)))
    num_elements = len(root_dir_list)
    dm = bcaw()
    #root_path = '/'
    #new_path = root_path
    if root_path == '/':
        new_path = ""
    else:
        new_path = root_path
    for item in root_dir_list:
        if item['isdir'] == True:
            ## print("D1: It is a Directory", item['name'])
            if item['name'] == '.' or item['name'] == '..':
                continue
            new_path = new_path + '/'+ str(item['name'])

            dfxml_file = image_path + "_dfxml.xml"

            new_path = bcaw_utils.bcawGetPathFromDfxml(str(item['name']), dfxml_file)
            ## print("D: bcawDnldRepo: path from Dfxml file: ", new_path)

            directory_path = app.config['FILES_TO_INDEX_DIR'] + "/" + new_path
            ## print ("D1: bcaDnldRepo: Trying to create directory ", directory_path)

            if not os.path.exists(directory_path):
                cmd = "mkdir " + re.escape(directory_path)
                ## print("bcawDnldRepo: Creating directry with command: ", cmd)
                try:
                    shelloutput = subprocess.check_output(cmd, shell=True)
                except subprocess.CalledProcessError as cmdexcept:
                    print "Error code: ", cmdexcept.returncode, cmdexcept.output
                ## print("D2: Created directory {}".format(directory_path))

            # Generate the file-list under this directory
            new_filelist_root, fs = dm.bcawGenFileList(image_path, image_index, partnum, new_path)
            # Call the function recursively
            ## print("bcawDnldRepo: Calling func recursively with item-name: {}, new_path:{}, item: {}".format(item['name'], new_path, item))
            bcawDnldRepo(img, new_filelist_root, fs, image_index, partnum, image_path, new_path)
        else:
            ## print("D2: bcawDnldRepo: It is a File", item['name'])
            filename = item['name'] # FIXME: Test more to make sure files with space work.

            #if item['name_slug'] != "None" and item['inode'] == int(inode) :
            if item['name_slug'] != "None" :

                # Strip the digits after the last "-" from filepath to get inode
                #new_filepath, separater, inode = filepath.rpartition("-")
                ## print("D >> Found a slug name ",item['name'], item['name_slug'])
                filename = item['name_slug']

            # If it is indexable file, download it and generate index.
            if (filename.endswith('.txt') or filename.endswith('.pdf') or filename.endswith('.xml') or filename.endswith('.doc')):

                ## print "D2: bcawDnldRepo: Indexing file {} in dir {}".format(filename, dirFilesToIndex)
                dfxml_file = image_path + "_dfxml.xml"
                ## print("D2: bcawDnldRepo: Calling bcawGetPathFromDfxml: dfxml_file: ", dfxml_file)
                # We will use the 'real' file name while looking for it in dfxml file
                new_file_path = bcaw_utils.bcawGetPathFromDfxml(item['name'], dfxml_file)

                # If there is space in the file-name, replace it by %20
                new_file_path = new_file_path.replace(" ", "%20")

                file_path = app.config['FILES_TO_INDEX_DIR'] + "/" + str(new_file_path)
                ## print("D: bcawDnldRepo: Calling bcawDnldSingleFile function for path: ", file_path)

                ## print (">> Indexing Image:{}-{}, File: {}".format(img, partnum, file_path))
                bcawDnldSingleFile(item, fs, file_path, indexDir)

def bcawGetImageIndex(image, is_path):
    global image_list
    if (is_path == True):
        image_name = os.path.basename(image_path)
    else:
        image_name = image
    global image_list
    for i in range(0, len(image_list)):
        if image_list[i] == image_name:
            return i
        continue
    else:
        print("Image not found in the list: ", image_name)

#
# Template rendering for Image Listing
#
@app.route('/image/<image_name>')
def image(image_name):
    # print("D: Partitions: Rendering Template with partitions for img: ", image_name)
    num_partitions = bcaw.num_partitions_ofimg[str(image_name)]
    part_desc = []
    image_index =  bcawGetImageIndex(image_name, is_path=False)
    for i in range(0, num_partitions):
        ## print("D: part_disk[i={}]={}".format(i, bcaw.partDictList[image_index][i]))
        part_desc.append(bcaw.partDictList[image_index][i]['desc'])

    return render_template('fl_img_temp_ext.html',
                            image_name=str(image_name),
                            num_partitions=num_partitions,
                            part_desc=part_desc)

@app.route('/image/metadata/<image_name>')
def image_psql(image_name):
    ## print("D: Rendering DB template for image: ", image_name)

    image_index =  bcawGetImageIndex(image_name, is_path=False)

    '''
    return render_template("db_image_template.html", 
                           image_name = image_name,
                           image=image_db[int(image_index)])
    '''
    return render_template("db_image_template.html", 
                           image_name = image_name,
                           image=image_db_list[image_index])

#
# Template rendering for Directory Listing per partition
#
@app.route('/image/<image_name>/<image_partition>')
def root_directory_list(image_name, image_partition):
    print("D: Files: Rendering Template with files for partition: ",
                            image_name, image_partition)
    image_index = bcawGetImageIndex(str(image_name), False)
    dm = bcaw()
    image_path = image_dir+'/'+image_name
    file_list_root, fs = dm.bcawGenFileList(image_path, image_index,
                                             int(image_partition), '/')
    ## print("\nRendering template fl_part_temp_ext.html: ", image_name, image_partition, file_list_root)
    return render_template('fl_part_temp_ext.html',
                           image_name=str(image_name),
                           partition_num=image_partition,
                           file_list=file_list_root)

# FIXME: Retained for possible later use
def stream_template(template_name, **context):
    #print("In stream_template(): ", template_name)
    app.update_template_context(context)
    t = app.jinja_env.get_template(template_name)
    rv = t.stream(context)
    rv.enable_buffering(5)
    return rv


#
# Template rendering when a File is clicked
#
@app.route('/image/<image_name>/<image_partition>', defaults={'filepath': ''})
@app.route('/image/<image_name>/<image_partition>/<path:filepath>')

def file_clicked(image_name, image_partition, filepath):
    print("\nFile_clicked: Rendering Template for subdirectory or contents of a file: ",
          image_name, image_partition, filepath)

    # Strip the digits after the last "-" from filepath to get inode
    new_filepath, separater, inode = filepath.rpartition("-") 

    print("D: Inode Split of file-name: new_filepath={}, sep:{}, inode:{} ".format\
            (new_filepath, separater, inode)) 
    if separater == "-":
        filepath = new_filepath

    # print("D: Files: Rendering Template for subdirectory or contents of a file: ",
          ## image_name, image_partition, path)
    
    image_index = bcawGetImageIndex(str(image_name), False)
    image_path = image_dir+'/'+image_name

    file_name_list = filepath.split('/')
    file_name = file_name_list[len(file_name_list)-1]

    # print "D: File_path after manipulation = ", path

    # To verify that the file_name exsits, we need the directory where
    # the file sits. That is if tje file name is $Extend/$RmData, we have
    # to look for the file $RmData under the directory $Extend. So we
    # will call the TSK API fs.open_dir with the parent directory
    # ($Extend in this example)
    temp_list = filepath.split("/")
    temp_list = file_name_list[0:(len(temp_list)-1)]
    parent_dir = '/'.join(temp_list)

    ## print("D: Invoking TSK API to get files under parent_dir: ", parent_dir)

    # Generate File_list for the parent directory to see if the
    dm = bcaw()
    file_list, fs = dm.bcawGenFileList(image_path, image_index,
                                        int(image_partition), parent_dir)

    # Look for file_name in file_list
    for item in file_list:
        print("D: item-name={} slug_name={} file_name={} item_inode={} ".format\
            (item['name'], item['name_slug'], file_name, item['inode']))

        # NOTE: There is an issue with recognizing filenames that have spaces.
        # All the characters after the space are chopped off at the route. As a
        # work-around a "slug" name is maintained in the file_list for each such
        # file. In order to recognize and map the chopped version of a file , the
        # file name is appended by its inode number. So when it gets here, a file
        # with a real name "Great Lunch.txt" will look like: "Great_Lunch.txt-xxx"
        # where xxx is the inode number. (Underscore is used to replace the blank
        # just for getting an idea on the file name. What is really used to recognize
        # the file is the inode.
        # Another issue is with the downloader not recognizing the spaces.
        #
        real_file_name = file_name
        if item['name_slug'] != "None" and item['inode'] == int(inode) :
            print("D >> Found a slug name ",item['name'], item['name_slug'])
            #file_name =  item['name_slug'].replace("%20", " ")
            # NOTE: Even the downloader doesn't like spaces in files. To keep
            # the complete name of the file, spaces are replaced by %20. The name
            # looks ugly, but till a cleaner solution is found, this is the best
            # fix.
            file_name =  item['name_slug']
            real_file_name = item['name_slug'].replace("%20", " ")

            print("D: real_file_name: {} slug_name={} ".format(real_file_name, file_name))

        if item['name'] == real_file_name:
            print("D : File {} Found in the list: ".format(file_name))
            break
    else:
        print("D: File_clicked: File {} not found in file_list".format(file_name))
        # FIXME: Should we abort it here?

    if item['isdir'] == True:
        # We will send the file_list under this directory to the template.
        # So calling once again the TSK API ipen_dir, with the current
        # directory, this time.
        ## filepath = filepath.replace(' ', '_')
        file_list, fs = dm.bcawGenFileList(image_path, image_index,
                                        int(image_partition), filepath)
        # Generate the URL to communicate to the template:
        with app.test_request_context():
            url = url_for('file_clicked', image_name=str(image_name), image_partition=image_partition, filepath=filepath )

        '''
        ############ Work under progress
        #If user has signed in, see if there is config info
        if 'email' in session:
          email = session['email']
          try:
            if checked_list_dict[email] != None:
              print("THERE IS STUFF IN CONFIG ", checked_list_dict[email])
              ##for item in checked_list_dict[email]:
                  ##print("Querying ", item)
                  ##qry = BcawDfxmlInfo.query.filter_by(image_name=image_name AND fo_filename=
            else:
              print("CHECKED LIST is empty")
          else:
        ############
        '''
        '''
        if 'email' in session:
            # get config_list
        '''

        print (">> Rendering template with URL: ", url)
        return render_template('fl_dir_temp_ext.html',
                   image_name=str(image_name),
                   partition_num=image_partition,
                   filepath=filepath,
                   file_list=file_list,
                   ##email = email,
                   ##checked_list=checked_list_dict[email],
                   url=url)

    else:
        print(">> Downloading File: ", real_file_name)
        # It is an ordinary file
        f = fs.open_meta(inode=item['inode'])
    
        # Read data and store it in a string
        offset = 0
        size = f.info.meta.size
        BUFF_SIZE = 1024 * 1024

        total_data = ""
        while offset < size:
            available_to_read = min(BUFF_SIZE, size - offset)
            data = f.read_random(offset, available_to_read)
            if not data:
                # print("Done with reading")
                break

            offset += len(data)
            total_data = total_data+data 
            # print "Length OF TOTAL DATA: ", len(total_data)
           

        ###file_new = "'" + real_file_name + "'"
        mime = MimeTypes()
        mime_type, a = mime.guess_type(file_name)
        generator = (cell for row in total_data
                for cell in row)
        return Response(stream_with_context(generator),
                        mimetype=mime_type,
                        headers={"Content-Disposition":
                                    "attachment;filename=" + file_name })
        '''
        return render_template('fl_filecat_temp_ext.html',
        image_name=str(image_name),
        partition_num=image_partition,
        file_name=file_name,
        contents=str(data))
        #contents = data.decode("utf-8"))
        '''
@app.route('/testdb')
def testdb():
    '''
    if db_login.session.query("1").from_statement("SELECT 1").all():
        return 'It works.'
    else:
        return 'Something is broken.'
    '''
    if bcaw_db.db.session.query("1").from_statement("SELECT 1").all():
        return 'It works.'
    else:
        return 'Something is broken.'

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    ##session = dbinit()
    form = SignupForm()

    if request.method == 'POST':
        if form.validate() == False:
            return render_template('fl_signup.html', form=form)
        else:
            newuser = User(form.firstname.data, form.lastname.data, form.email.data, form.password.data)
            db_login.session.add(newuser)
            db_login.session.commit()

            session['email'] = newuser.email

            ##return "[1] Create a new user [2] sign in the user [3] redirect to the user's profile"
            return redirect(url_for('profile'))

    elif request.method == 'GET':
        return render_template('fl_signup.html', form=form)

@app.route('/home')
def home():
    #return render_template('fl_profile.html')
    # FIXME: There is code duplication here. Merge the folowing with bcawBrowse
    # and call from both places (root and /home)
    ####return(bcawBrowse(db_init=False))

    global image_dir
    image_index = 0

    # Since image_list is declared globally, empty it before populating
    global image_list
    del image_list[:]
    global image_db_list
    del image_db_list [:]

    # Create the DB. FIXME: This needs to be called from runserver.py 
    # before calling run. That seems to have some issues. So calling from
    # here for now. Need to fix it.
    for img in os.listdir(image_dir):
        if img.endswith(".E01") or img.endswith(".AFF"):
            ## print img
            ### global image_list
            image_list.append(img)

            dm = bcaw()
            image_path = image_dir+'/'+img
            dm.num_partitions = dm.bcawGetPartInfoForImage(image_path, image_index)
            idb = bcaw_db.BcawImages.query.filter_by(image_name=img).first()
            image_db_list.append(idb)
            ## print("D: IDB: image_index:{}, image_name:{}, acq_date:{}, md5: {}".format(image_index, idb.image_name, idb.acq_date, idb.md5)) 
            image_index +=1
        else:
            continue

    # Render the template for main page.
    # print 'D: Image_list: ', image_list
    global num_images
    num_images = len(image_list)

    user = "Sign In"
    signup_out = "Sign Up"
    if 'email' in session:
      user = session['email']
      signup_out = "Sign Out"

    qform = QueryForm()

    return render_template('fl_temp_ext.html', image_list=image_list, np=dm.num_partitions, image_db_list=image_db_list, user=user, signup_out = signup_out, form=qform)

@app.route('/about')
def about():
    return render_template('fl_profile.html')

@app.route('/contact')
def contact():
    return render_template('fl_profile.html')

@app.route('/profile')
def profile():
  if 'email' not in session:
    return redirect(url_for('signin'))
 
  user = User.query.filter_by(email = session['email']).first()
 
  if user is None:
    return redirect(url_for('signin'))
  else:
    return render_template('fl_profile.html')

@app.route('/config', methods=['POST','GET'])
def config():
  config_list = ['filename', 'po', 'sectsize', 'blksize']
  if 'email' not in session:
    return redirect(url_for('config'))

  user = User.query.filter_by(email = session['email']).first()
 
  if user is None:
    return redirect(url_for('signin'))
  else:
    config
    return render_template('fl_config.html', 
                   config_list=config_list,
                   num_config_items=str(len(config_list)))
    
@app.route('/fl_process_confinfo.html',  methods=['POST','GET'])
def fl_process_confinfo():
    checked_list = request.form.getlist('config_item')
    print("Checked File list: ", checked_list)

    '''
    email = session['email']

    checked_list_dict[email] = checked_list
    '''

    # FIXME: This needs to be made persistent
    if 'email' in session:
        email = session['email']
        print("D: Adding Email ", email)
        checked_list_dict[email] = checked_list

    print("D: Checked DICT: ", checked_list_dict)


    return render_template('fl_process_confinfo.html', checked_list=checked_list)
    #return render_template('fl_process_confinfo.html')

@app.route('/signin', methods=['GET', 'POST'])
def signin():
  form = SigninForm()
  if request.method == 'POST':
    if form.validate() == False:
      return render_template('fl_signin.html', form=form)
    else:
      session['email'] = form.email.data
      return redirect(url_for('profile'))
  elif request.method == 'GET':
    return render_template('fl_signin.html', form=form)

@app.route('/signout')
def signout():
  if 'email' not in session:
    return redirect(url_for('signin'))

  session.pop('email', None)
  return redirect(url_for('home'))
'''
def bcaw_query(db, phrase):
    query = db.session.query()
    query = search(query, phrase)

    print("D: ", query.first().name)
'''

@app.route('/query', methods=['GET', 'POST'])
def query():
    form = QueryForm()
    if request.method == 'POST':
        search_result_file_list = []
        search_result_image_list = []
        searched_phrase = form.search_text.data.lower()

        search_result_list, search_type = form.searchDfxmlDb()
        if search_type == "filename":
            if search_result_list == None:
                print "No search results for ", searched_phrase
                num_results = 0
            else:
                i = 0
                # Note; For now, two separae lists are maintained - one for filename
                # and another for the corresponding image. If we need more than two
                # columns to display then it makes sense to have an array of structues
                # instead of 2 separate lists.
                for list_item in search_result_list:
                    #search_result_file_list[i] = list_item.fo_filename
                    search_result_file_list.append(list_item.fo_filename)
                    search_result_image_list.append(list_item.image_name)
                    ## print("search_result_file_list[{}] = {}, img: {} ".format(i, search_result_file_list[i], list_item.image_name))
                    i += 1
                print "D: query:Result:len: {}, file: {} ".format(len(search_result_list), search_result_list[0].fo_filename)

                num_results = len(search_result_list)
        else: # search type is "Contents"
            if search_result_list == None:
                print ">> No search results for ", searched_phrase
                num_results = 0
            else:
                ## print "D2: search result list: ", search_result_list
                num_results = len(search_result_list)
                search_result_file_list = search_result_list

        if search_result_list == None:
            print ">> Query: searchDfxmlDb FAILED "
            num_results = 0
        else:
            print ">> Searched for ", searched_phrase

        user = "Sign In"
        signup_out = "Sign Up"
        if 'email' in session:
          user = session['email']
          signup_out = "Sign Out"

        print (">> Rendering template with URL:  ")
        return render_template('fl_search_results.html',
                                searched_phrase=searched_phrase,
                                num_results=num_results,
                                search_result_file_list=search_result_file_list,
                                search_result_image_list=search_result_image_list,
                                user=user, signup_out = signup_out, form=form)
                                                    
            
    elif request.method == 'GET':
        return render_template('fl_query.html', form=form)
        

    ##query = bcaw_query(BcawDfxmlInfo, phrase) 
    #engine = create_engine('postgresql://vagrant:vagrant@localhost/bca_db')

    '''
    engine = create_engine('postgresql://vagrant:vagrant@localhost/bca_db')

    #Base.metadata.create_all(engine)
    db_login.Model.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    session = Session()

    query1 = session.query(bcaw_db.BcawDfxmlInfo)

    print("QUERY PASSED ")
    #print(query1)

    ####query = search(query1, 'astronaut.jpg', vector=bcaw_db.BcawDfxmlInfo.fo_filename)
    query = search(query1, 'astronaut.jpg', vector=bcaw_db.BcawDfxmlInfo.fo_filename)

    print("query: ", query)


    print query.first()

    ####query = db_login.session.query()
    ####query = search(query, 'Email')

    #print("query.first.fo_filename : ", query.first().fo_filename)
    return render_template("fl_profile.html")
    '''

def bcaw_generate_file_list():
    """ Using dfxml file, this routine filters the lines containing filename and
        puts them in a file to use as an input to the indexing function.
        This is done in order to provide a search option to look for filenames
        using lucene indexing as opposed to a DB query.
        FIXME: Currently this method is not providing very useful info compared
        to the db query. This needs some more thinking to make it more useful
    """
    outfile_dir = app.config['FILENAME_INDEXDIR']
    outfile = outfile_dir + '/filelist_to_index.txt'
    print "D: bcaw_generatefile_list: Creating : ", outfile, outfile_dir

    if not os.path.exists(outfile_dir):
        subprocess.check_output("mkdir " + outfile_dir, shell=True) 
    subprocess.check_output("touch " + outfile, shell=True)
    for dfxml_file in os.listdir(image_dir):
        if dfxml_file.endswith("_dfxml.xml"):
            print "Listing files from dfxml file: ", dfxml_file
            file_list_cmd ="cd "+ image_dir + "; rm -rf tempdir; mkdir tempdir; " + "grep '\<filename\>' " + dfxml_file + " > tempdir/file1; sed \'s/<filename>//g\' tempdir/file1 > tempdir/file2; sed \'s/<\/filename>//g\' tempdir/file2 > tempdir/file3;"
            print("D: bcaw_generate_file_list: File_list_cmd: ", file_list_cmd)

            try:
                subprocess.check_output(file_list_cmd, shell=True)
            except subprocess.CalledProcessError as cmdexcept:
                print "file_list_cmd failed. Error Code: ", cmdexcept.returncode, cmdexcept.output

            cat_cmd =  "cat " + image_dir + "/tempdir/file3 >> " + outfile
            subprocess.check_output(cat_cmd, shell=True)

    print "Returning outfile: ", os.path.dirname(outfile)
    return os.path.dirname(outfile)

def bcawSetIndexFlag(image_index):
    """ This routine sets the index flag in the image matrix, for the image
        corresponding to the given image_index.
    """
    for img_tbl_item in image_matrix:
        if img_tbl_item['img_index'] == image_index:
            img_tbl_item.update({bcaw_imginfo[4]:1})
            ## print "[D] Image Matrix After setting Index flag: ", image_matrix
            break
    else:
        print ">> bcawSetIndexFlag: image_index not found ", image_index

def bcawSetFlagInMatrix(flag, value, image_name):
    """ This routine sets the given flag (in bcaw_imginfo) to the given value,
        in the image matrix, for all the images present.
    """
    print "[D] bcawSetFlagInMatrix: flag, value: ", flag, value, image_name
    print "[D] bcawSetFlagInMatrix: Image Matrix Before: ", image_matrix
    i = 0
    for img_tbl_item in image_matrix:
        if flag == 'img_name':
            if img_tbl_item['img_name'] == image_name:
                img_tbl_item.update({bcaw_imginfo[4]:1})
                break

        elif flag == 'img_db_exists':
            # Set img_db_exists to the given value for every image in the image_table
            if img_tbl_item['img_name'] == image_name:
                img_tbl_item.update({bcaw_imginfo[2]:value})
                img_tbl_item.update({bcaw_imginfo[1]:image_name})
                print "[D] Setting flag img_db_exists in the image matrix for image ", image_name
                break
            else:
                # Update the flag for all images
                img_tbl_item.update({bcaw_imginfo[2]:value})

        elif flag == 'dfxml_db_exists':
            # Set dfxml_db_exists to the given value for every image in the image_table
            if img_tbl_item['img_name'] == image_name:
                print "[D] Setting flag dfxml_db_exists to {} in the image matrix for image {}".format(value, image_name)
                img_tbl_item.update({bcaw_imginfo[3]:value})
                img_tbl_item.update({bcaw_imginfo[1]:image_name})
                break
            else:
                # Update the flag for all images
                img_tbl_item.update({bcaw_imginfo[3]:value})

        i += 1
    return

    ## print "[D] bcawSetFlagInMatrix: Image Matrix After setting the falg: ", image_matrix
def bcawSetFlagInMatrixPerImage(flag, value, image):
    """ This routine sets the given flag (in bcaw_imginfo) to the given value,
        in the image matrix, for all the images present.
    """
    ## print "[D] bcawSetFlagInMatrix: flag, value: ", flag, value
    ## print "[D] bcawSetFlagInMatrix: Image Marix Before: ", image_matrix
    i = 0
    for img_tbl_item in image_matrix:
        if flag == 'img_index':
            if img_tbl_item['img_index'] == image_index:
                img_tbl_item.update({bcaw_imginfo[4]:1})
                break

        elif flag == 'img_db_exists':
            ## print "[D] Setting flag img_db_exists in the image matrix"
            # Set img_db_exists to the given value for every image in the image_table
            img_tbl_item.update({bcaw_imginfo[2]:value})

        elif flag == 'dfxml_db_exists':
            ## print "[D] Setting flag dfxml_db_exists in the image matrix"
            # Set dfxml_db_exists to the given value for every image in the image_table
            img_tbl_item.update({bcaw_imginfo[3]:value})

        i += 1

def bcawIsImgInMatrix(img):
    for img_tbl_item in image_matrix:
        if img_tbl_item['img_name'] == img:
            ## print "[D]Image {} found in the marix. ".format(img)
            return True
    else:
        ## print "image {} NOT found in the matrix ".format(img)
        return False

def bcawIndexAllFiles():
    global image_list
    global image_db_list
    global partition_in
    global image_dir
    ## print "[D] bcawIndexAllFiles: image_list: ", image_list
    ## print "[D] bcawIndexAllFiles: image_db_list: ", image_db_list

    # First, create the directory FILES_TO_INDEX_DIR if doesn't exist
    files_to_index_dir = app.config['FILES_TO_INDEX_DIR']
    if not os.path.exists(files_to_index_dir):
        cmd = "mkdir " + files_to_index_dir
        subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT)

    image_index = 0
    for img in os.listdir(image_dir):
        print(">> Building Index for image: ", img)
        if img.endswith(".E01") or img.endswith(".AFF"):
            # If index exists for this image, don't do it
            # FIXME: Query lucene to check the existance of indexing for this 
            # image and continue to the next image if indexing exiss for this img.
            # Code needs to be added.

            dm = bcaw()
            image_path = image_dir+'/'+img
            #dm.num_partitions = dm.bcawGetPartInfoForImage(image_path, image_index)

            print("bcawIndexAllFiles: parts: ", partition_in[img])
            temp_root_dir = "/vagrant"
            for p in range(0, partition_in[img]):
                # make the directory for this img and partition
                part_dir = str(temp_root_dir) + '/img'+str(image_index)+"_"+ str(p)

                ## print("Part Dir: ", part_dir)
                #os.makedir(part_dir)
                file_list_root, fs = dm.bcawGenFileList(image_path, image_index,
                                             int(p), '/')
                ## print("D: Calling bcawDnldRepo with root ", file_list_root)
                # NOTE: The following is under construction. Hence commented out.
                ####bcawDnldRepo(file_list_root, part_dir, image_index, p, image_path, '/')
                bcawDnldRepo(img, file_list_root, fs, image_index, p, image_path, '/')

            # If successfully indexed, set the flag to "indexed" in the image table
            bcawSetIndexFlag(image_index)

            image_index += 1

@app.route('/admin', methods=['GET', 'POST'])
def admin():
  form = adminForm()
  if request.method == 'POST':
    db_option = 3
    db_option_msg = None
    if (form.radio_option.data.lower() == 'all_tables'):
        print ">> Admin: Requested all tables build "
        db_option = 1
        db_option_msg = "Built All the Tables"

        # Add Tables - either image table, or DFXML table or both - to the DB
        # based on the arguments.
        retval, db_option_msg = bcaw_db.dbBuildDb(bld_imgdb = True, bld_dfxmldb = True)
    elif(form.radio_option.data.lower() == 'image_table'):
        print ">> Admin: Requested Image table build "
        # First check if the particular image exists. If it does, don't build
        # another entry for the same image.
        # NOTE: db_option is not really used at this time. Just keeping it in
        # case it could be of use in the future. Will be removed while cleaning up,
        # if not used.
        db_option = 2
        retval, db_option_msg = bcaw_db.dbBuildDb(bld_imgdb = True, bld_dfxmldb = False)
    elif (form.radio_option.data.lower() == 'dfxml_table'):
        print ">> Admin: Requested DFXML table build "
        db_option = 3
        retval, db_option_msg = bcaw_db.dbBuildDb(bld_imgdb = False, bld_dfxmldb = True)
        if retval == 0:
            db_option_msg = "Built DFXML Table"
    elif (form.radio_option.data.lower() == 'drop_all_tables'):
        print ">> Admin: Requested Image and DFXML DB Drop "
        db_option = 4
        ## print "[D]: Dropping img table and updating the matrix for img_db_exists "
        retval_img, message_img = bcaw_db.dbu_drop_table("bcaw_images")

        # update the image_matrix
        bcawSetFlagInMatrix('img_db_exists', False, None)

        ## print "[D] Dropping dfxml table and updating the matrix for dfxml_db_exists "
        retval_dfxml, message_dfxml = bcaw_db.dbu_drop_table("bcaw_dfxmlinfo")

        # update the image_matrix
        bcawSetFlagInMatrix('dfxml_db_exists', False, None)

        if retval_img == 0 and retval_dfxml == 0:
            db_option_msg = "Dropped all tables "
        elif retval_img == -1 and retval_dfxml == -1:
            db_option_msg = "Failed to drop all tables. Tables might not exist "
        else:
            db_option_msg = message_img
    elif (form.radio_option.data.lower() == 'drop_img_table'):
        print ">> Admin: Requested Image DB Drop "
        ## print "[D] Dropping img table and updating the matrix for img_db_exists "
        db_option = 5
        retval, db_option_msg = bcaw_db.dbu_drop_table("bcaw_images")

        # update the image_matrix
        bcawSetFlagInMatrix('img_db_exists', False, None)

    elif (form.radio_option.data.lower() == 'drop_dfxml_table'):
        print ">> Admin: Requested DFXML DB Drop "
        ## print "[D] Dropping dfxml table and updating the matrix for dfxml_db_exists "
        db_option = 5
        retval, db_option_msg = bcaw_db.dbu_drop_table("bcaw_dfxmlinfo")

        # update the image_matrix
        bcawSetFlagInMatrix('dfxml_db_exists', False, None)

    elif (form.radio_option.data.lower() == 'generate_index'):
        # First biuld the index for th filenames. Then build the index
        # for the contents from the configured directory. The contents index
        # is built in 
        db_option = 6
        db_option_msg = "Option not yet supported"
        dirFileNamesToIndex = bcaw_generate_file_list()
        if os.path.exists(dirFileNamesToIndex):
            ## print("[D]: Indexing Filenames ")
            index_dir = app.config['FILENAME_INDEXDIR']
            bcaw_index.IndexFiles(dirFileNamesToIndex, index_dir)
            print(">> Filename Index built in directory ", index_dir)
            db_option_msg = "Index built"
        # Now build the indexes for the content files fromn directory files_to-index

        # First get the files starting from the root, for each image listed
        bcawIndexAllFiles()

        # FIXME: Get the return code from bcawIndexAllFiles to set db_option_msg.
        # Till now, we will assume success.
        db_option_msg = "Index built"

        if os.path.exists(dirFilesToIndex) :
            print ">> Building Indexes for contents in ", dirFilesToIndex
            bcaw_index.IndexFiles(dirFilesToIndex, indexDir)
            print ">> Built indexes for contents in ", indexDir
    elif (form.radio_option.data.lower() == 'show_image_matrix'):
        db_option = 7
        db_option_msg = "Image Matrix "
        # Send the image list to the template
        ## print "[D] Displaying Image Matrix: ", image_matrix
        build_form = buildForm()
        return render_template('fl_admin_imgmatrix.html',
                           db_option=str(db_option),
                           db_option_msg=str(db_option_msg),
                           image_matrix=image_matrix,
                           build_form=build_form,
                           form=form)

    # request.form will be in the form:
    # ImmutableMultiDict([('delete_table, <image>), ), )'delete_form', 'submit')])
    # We need the image name from this dict. So we use the first element of the
    # list to get the image name so we know which image DB the table is being added
    # to or deleted from. 
    bld_list = request.form.getlist('build_table')
    delete_list = request.form.getlist('delete_table')

    ## print "D2: Build_list: ", bld_list
    ## print "D2: Delete_list: ", delete_list

    checked_build = 'build_table' in request.form
    checked_delete = 'delete_table' in request.form

    if checked_build or checked_delete:

        ## print "D2: checked_build ", checked_build
        ## print "D2: checked_delete: ", checked_delete
        if checked_build == True and checked_delete == True:
            db_option_msg = "Invalid combination of checked boxes"
        elif checked_build == True:
            print "D: Checked build: build_table_list: ", bld_list[0]
            image_name = bld_list[0]

            if bld_list[0] == 'submit':
                # This means no image is selected.
                print ">> No image selected. Returning"
                db_option_msg = "Error: No Image Selected"
            elif bcaw_db.dbu_does_table_exist_for_img(image_name, 'bcaw_dfxmlinfo'):
                # First check if the dfxml table entry exists for this image.
                print ">> Table bcaw_dfxmlinfo already exists in the DB "
                db_option_msg = "Table bcaw_dfxmlinfo already exists for image " + image_name
                print ">> Building DFXML table for image ", image_name 
                retval, db_option_msg = bcaw_db.dbBuildTableForImage(image_name, bld_imgdb = False, bld_dfxmldb = True)
                if retval == 0:
                    db_option_msg = "Built DFXML Table"
        elif checked_delete == True:
            print "D: delete_table_list: ", delete_list[0]
            image_name = delete_list[0]

            if delete_list[0] == 'submit':
                # This means no image is selected.
                print ">> No image selected. Returning"
                db_option_msg = "Error: No Image Selected"
            elif not bcaw_db.dbu_does_table_exist_for_img(image_name, 'bcaw_dfxmlinfo'):
                # First check if the dfxml table entry exists for this image.
                print ">> Table bcaw_dfxmlinfo does not exist in the DB "
                db_option_msg = "Table bcaw_dfxmlinfo does not exist for image " + image_name
            else:
                print ">> Deleting Entries for image {} from dfxml table".format(image_name)
                retval, db_option_msg = \
                   bcaw_db.dbu_execute_dbcmd("bcaw_dfxmlinfo", "delete_entries_for_image", image_name)

    return render_template('fl_admin_results.html',
                           db_option=str(db_option),
                           db_option_msg=str(db_option_msg),
                           form=form)
 
  elif request.method == 'GET':
    return render_template('fl_admin.html', form=form)
 
  if 'email' not in session:
    return redirect(url_for('admin'))
 
  user = User.query.filter_by(email = session['email']).first()
 
'''
  if user is None:
    return redirect(url_for('signin'))
  else:
    # Check if user has the permission to do admin services
    return render_template('fl_profile.html')   # FIXME: Placeholder
'''    

# FIXME: This is never called (since we run runserver.py)
# Remove once confirmed to be deleted
if __name__ == "__main__":
    dm = bcaw()
    bcaw_db.bcawdb()
    app.run()
