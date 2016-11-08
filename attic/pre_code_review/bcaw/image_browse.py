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
# This file contains the main BitCurator Access Webtools application.
#

from flask import Flask, render_template, url_for, Response, stream_with_context, request, flash, session, redirect, jsonify
from bcaw_forms import ContactForm, SignupForm, SigninForm, QueryForm, adminForm
from celery import Celery

import pytsk3
import os, sys, string, time, re, urllib
import logging
from mimetypes import MimeTypes
from datetime import date
from bcaw_utils import bcaw
from bcaw_utils import *
import lucene
import bcaw_celery_task

from bcaw import app
import bcaw_db
import bcaw_index
from sqlalchemy import *
from bcaw_userlogin_db import db_login, User, dbinit
from werkzeug.routing import BaseConverter

import subprocess
from subprocess import Popen,PIPE
from flask import send_from_directory

image_list = []
file_list_root = []
checked_list_dict = dict()
partition_in = dict()

# image_matrix is a global list of dictioaries, bcaw_imginfo, one per image.
image_matrix = []
bcaw_imginfo = ['img_index', 'img_name', 'img_db_exists', 'dfxml_db_exists', 'index_exists']

# task_id_table os a dictionary containing the asynchronous task_id per async feature.
# Currently there is on for Indexing task and the task that builds dfxml table in the
# db. It can be expanded as needed. The value will be populated when the async task
# is invoked. This table is used by taskstatus. Originally the task_id was being passed
# to the taskstatus route. But to avoid a url with dynamically generated task_id,
# it was decided to store the task_id in a table and use it instead.
task_id_table = {'Indexing':0, 'Build_dfxml_tables':0, 'Build_all_tables':0}
task_response_table = {'Indexing':None, 'Build_dfxml_tables':None, 'Build_all_tables':None}

def bcawPopulateImgInfoTable(image_index, img, imgdb_flag, dfxmldb_flag, index_flag):
    """ For the given image (img), this routine updates the corresponding
        fields of bcaw_imginfo within the list image_matrix.
        FIXME: Yet to add code to update index flag.
    """
    if img:
        img_db_exists = False
        dfxml_db_exists = False
        img_is_indexed = False

        # Query the DB to see if tables exist for the given image.
        if bcaw_db.dbu_does_table_exist_for_img(img, "bcaw_images"):
            img_db_exists = True

            # Query the DB to see this image is indexed. We use a field in the
            # image table to store this information.
            if bcawIsImageIndexedInDb(img) == True:
                logging.debug('[D2]:bcawPopulateImgInfoTable: Image %s is index ', img)
                img_is_indexed = True

        if bcaw_db.dbu_does_table_exist_for_img(img, "bcaw_dfxmlinfo"):
            dfxml_db_exists = True

        # Add the querried info to the matrix.
        image_matrix.append({bcaw_imginfo[0]:image_index, bcaw_imginfo[1]:img, bcaw_imginfo[2]:img_db_exists, bcaw_imginfo[3]:dfxml_db_exists, bcaw_imginfo[4]:img_is_indexed})

#FIXME: The following line should be called in __init__.py once.
# Since that is not being recognized here, app.config.from_object is
# added here. This needs to be fixed.
image_dir = app.config['IMAGEDIR']
dirFilesToIndex = app.config['FILES_TO_INDEX_DIR']
indexDir = app.config['INDEX_DIR']

# CELERY stuff
celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)

num_images = 0
image_db_list = []

@app.route("/home")
def home():
    return redirect(url_for("bcawBrowseImages"), code=302)

@app.route('/')
def bcawBrowseImages():
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

    dm = bcaw()
    for img in os.listdir(image_dir):
        if bcaw_is_imgtype_supported(img):
            image_list.append(img)
            image_path = image_dir+'/'+img
            dm.num_partitions = dm.bcawGetPartInfoForImage(image_path, image_index)
            idb = bcaw_db.BcawImages.query.filter_by(image_name=img).first()
            partition_in[img] = dm.num_partitions
            image_db_list.append(idb)

            # Populate the image info table with this image name and index
            if bcawIsImgInMatrix(img):
                logging.debug('[D]Not populating the image matrix as it already exists for image %s ', img)
            else:
                bcawPopulateImgInfoTable(image_index, img, 0, 0, 0)
                image_index +=1
        else:
            continue

    ### global partition_in

    # Render the template for main page.
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
            break

        offset += len(data)
        total_data = total_data+data

    with open(filepath, "w") as text_file:
        text_file.write(total_data)

    basepath = os.path.dirname(filepath)
    bcaw_index.IndexFiles(basepath, index_dir)

    rmcmd = "rm " + '"' + filepath + '"'
    subprocess.check_output(rmcmd, shell=True, stderr=subprocess.STDOUT)

    if filepath.endswith('.pdf'):
        filepath_txt = filepath.replace('.pdf', '.txt')
        rmcmd_1 = "rm " + '"' + filepath_txt + '"'
        if os.path.exists(filepath_txt):
            subprocess.check_output(rmcmd_1, shell=True, stderr=subprocess.STDOUT)

def isFileIndexable(filename):
    if (filename.endswith('.txt') or filename.endswith('.TXT') or  \
        filename.endswith('.pdf') or filename.endswith('.PDF') or \
        filename.endswith('.xml') or filename.endswith('.XML') or \
        filename.endswith('.doc') or filename.endswith('.DOC') or \
        filename.endswith('.htm') or filename.endswith('.HTM;1') or \
        filename.endswith('.html') or filename.endswith('.HTML') ):
        return True
    else:
        return False

@celery.task
def bcawDnldRepo(img, root_dir_list, fs, image_index, partnum, image_path, root_path):
    """This routine is used to download the indexable files of the Repository
    """

    num_elements = len(root_dir_list)
    dm = bcaw()
    if root_path == '/':
        new_path = ""
    else:
        new_path = root_path

    for item in root_dir_list:
        if item['isdir'] == True:
            logging.debug("bcawDnldRepo: D1:It is a Directory", item['name'])
            if item['name'] == '.' or item['name'] == '..':
                continue

            if new_path == None:
               continue

            new_path = new_path + '/'+ str(item['name'])

            dfxml_file = image_path + "_dfxml.xml"

            new_path = bcawGetPathFromDfxml(str(item['name']), dfxml_file)
            if new_path == None:
               continue

            # We will add image_index to the path so we can later extract the
            # image name to be displayed. We could have passed the image name
            # itself, instead of the index, but if the image name has special
            # characters, we might bump into unexpected errors while creating
            # files/directories with an unknown string. So chose to use the image
            # index here and later extract the corresponding image name.
            directory_path = app.config['FILES_TO_INDEX_DIR']+"/"+str(image_index) +"/"+new_path

            if not os.path.exists(directory_path):
                cmd = "mkdir " + re.escape(directory_path)
                try:
                    shelloutput = subprocess.check_output(cmd, shell=True)
                except subprocess.CalledProcessError as cmdexcept:
                    logging.error('Error return code: %s ', cmdexcept.returncode)
                    logging.error('Error output: %s ', cmdexcept.output)

            # Generate the file-list under this directory
            new_filelist_root, fs = dm.bcawGenFileList(image_path, image_index, partnum, new_path)

            # if file_list is None, continue
            if new_filelist_root == None:
                continue

            # Call the function recursively
            bcawDnldRepo(img, new_filelist_root, fs, image_index, partnum, image_path, new_path)
        else:
            filename = item['name'] # FIXME: Test more to make sure files with space work.

            # If it is indexable file, download it and generate index.
            if isFileIndexable(filename):

                dfxml_file = image_path + "_dfxml.xml"
                # We will use the 'real' file name while looking for it in dfxml file
                new_file_path = bcawGetPathFromDfxml(item['name'], dfxml_file)

                # If there is space in the file-name, replace it by %20
                new_file_path = new_file_path.replace(" ", "%20")

                file_path = app.config['FILES_TO_INDEX_DIR'] + "/" + str(image_index) + "/" + str(new_file_path)

                logging.debug("Indexing Image:{}-{}, File: {}".format(img,\
                                  partnum, file_path))
                bcawDnldSingleFile(item, fs, file_path, indexDir)

def bcawGetImageIndex(image, is_path):
    global image_list
    if (is_path == True):
        image_name = os.path.basename(image_path)
    else:
        image_name = image
    for i in range(0, len(image_list)):
        if image_list[i] == image_name:
            return i
        continue
    else:
        logging.debug('Image %s not found in image_list.', image_name)

#
# Template rendering for Image Listing
#
@app.route('/image/imgdnld/<image_name>/')
def image_dnld(image_name):
    source_dir = app.config['IMAGEDIR']
    return send_from_directory(source_dir, image_name, as_attachment=True)

@app.route('/image/metadata/<image_name>/')
def image_psql(image_name):

    image_index =  bcawGetImageIndex(image_name, is_path=False)
    meta = bcaw_is_sysmeta_supported(image_name)
    return render_template("db_image_template.html",
                           image_name = image_name,
                           image=image_db_list[image_index],
                           meta=meta)

@app.route('/image/<image_name>/')
def image(image_name):
    num_partitions = bcaw.num_partitions_ofimg[str(image_name)]
    part_desc = []
    image_index =  bcawGetImageIndex(image_name, is_path=False)

    # Find the file-system type first. For fat12, fat16, raw images, there is no
    # partition info. We need to skip the step for such cases.
    #FIXME: This is taken care of elsewhere in the code. Check.

    for i in range(0, num_partitions):
        part_desc.append(bcaw.partDictList[image_index][i]['desc'])

    return render_template('fl_img_temp_ext.html',
                            image_name=str(image_name),
                            num_partitions=num_partitions,
                            part_desc=part_desc)

#
# Template rendering for Directory Listing per partition
#
@app.route('/image/<image_name>/<image_partition>/')
def root_directory_list(image_name, image_partition):
    logging.debug('Rendering Template with files for partition: %s', image_partition)
    image_index = bcawGetImageIndex(str(image_name), False)
    dm = bcaw()
    image_path = image_dir+'/'+image_name
    file_list_root, fs = dm.bcawGenFileList(image_path, image_index,
                                             int(image_partition), '/')
    return render_template('fl_part_temp_ext.html',
                           image_name=str(image_name),
                           partition_num=image_partition,
                           file_list=file_list_root)

#
# Template rendering when a File is clicked
#
@app.route('/image/<image_name>/<image_partition>/', defaults={'encoded_filepath': ''})
@app.route('/image/<image_name>/<image_partition>/<path:encoded_filepath>/')
def file_clicked(image_name, image_partition, encoded_filepath):
    logging.debug('File_clicked: Rendering Template for subdirectory or contents of a file ')
    # Strip the digits after the last "-" from filepath to get inode

    image_index = bcawGetImageIndex(str(image_name), False)
    image_path = image_dir+'/'+image_name
    filepath=urllib.unquote(encoded_filepath)
    file_name_list = filepath.split('/')
    file_name = file_name_list[len(file_name_list)-1]

    # To verify that the file_name exsits, we need the directory where
    # the file sits. That is if the file name is $Extend/$RmData, we have
    # to look for the file $RmData under the directory $Extend. So we
    # will call the TSK API fs.open_dir with the parent directory
    # ($Extend in this example)
    temp_list = filepath.split("/")
    temp_list = file_name_list[0:(len(temp_list)-1)]
    parent_dir = '/'.join(temp_list)


    # Generate File_list for the parent directory to see if the
    dm = bcaw()
    file_list, fs = dm.bcawGenFileList(image_path, image_index,
                                        int(image_partition), parent_dir)

    # Look for file_name in file_list
    for item in file_list:
        if item['name'] == file_name:
            break
    else:
        logging.warning('Requested file %s not found in file_list', file_name)
        # FIXME: Should we abort it here?

    if item['isdir'] == True:
        # We will send the file_list under this directory to the template.
        # So calling once again the TSK API ipen_dir, with the current
        # directory, this time.
        file_list, fs = dm.bcawGenFileList(image_path, image_index,
                                        int(image_partition), filepath)
        # Generate the URL to communicate to the template:
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

        logging.debug('Rendering template with filepath:%s', filepath)
        return render_template('fl_dir_temp_ext.html',
                   image_name=str(image_name),
                   partition_num=image_partition,
                   filepath=filepath,
                   file_list=file_list)

    else:
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

        mime = MimeTypes()
        mime_type, a = mime.guess_type(file_name)
        generator = (cell for row in total_data
                for cell in row)
        return Response(stream_with_context(generator),
                        mimetype=mime_type,
                        headers={"Content-Disposition":
                                    "attachment;filename=" + file_name })

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    form = SignupForm()

    if request.method == 'POST':
        if form.validate() == False:
            return render_template('fl_signup.html', form=form)
        else:
            newuser = User(form.firstname.data, form.lastname.data, form.email.data, form.password.data)
            db_login.session.add(newuser)
            db_login.session.commit()

            session['email'] = newuser.email

            return redirect(url_for('profile'))

    elif request.method == 'GET':
        return render_template('fl_signup.html', form=form)

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

    # FIXME: This needs to be made persistent
    if 'email' in session:
        email = session['email']
        checked_list_dict[email] = checked_list

    return render_template('fl_process_confinfo.html', checked_list=checked_list)

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

@app.route('/query', methods=['GET', 'POST'])
def query():
    global image_list
    form = QueryForm()
    if request.method == 'POST':
        search_result_file_list = []
        search_result_image_list = []
        searched_phrase = form.search_text.data.lower()

        search_result_list, search_type = form.searchDfxmlDb()
        if search_result_list == None:
            logging.info('No search results for %s', searched_phrase)
            num_results = 0
        elif search_type == "filename":
            i = 0
            # Note; For now, two separae lists are maintained - one for filename
            # and another for the corresponding image. If we need more than two
            # columns to display then it makes sense to have an array of structues
            # instead of 2 separate lists.
            for list_item in search_result_list:
                search_result_file_list.append(list_item.fo_filename)
                search_result_image_list.append(list_item.image_name)
                i += 1
            num_results = len(search_result_list)
        else: # search type is "Contents"
            # The search results list will have the unncessary leading text
            # for each result. We will chop it off. But the last part of the
            # string contains the image name, which is a usefule info for us
            # do send to the template. Some string and list manipulations
            # done here to extract the useful info and get rid of the unwanted
            # stuff. NOTE: There could be a better and more efficient way of
            # doing the same. We will address it later.
            search_result_list = [w.replace('/var/www/bcaw/files_to_index/', '') for w in search_result_list]
            index = 0
            search_result_image_list = []
            for j in search_result_list:
                j_list = j.split("/")
                j_index = int(j_list[0])
                j_image = image_list[j_index]
                search_result_image_list.append(j_image)

                # Now remove the leading index number from the fielname
                j_list.pop(0)
                search_result_list[index] = "/".join(j_list)
                index += 1

            num_results = len(search_result_list)
            search_result_file_list = search_result_list

        user = "Sign In"
        signup_out = "Sign Up"
        if 'email' in session:
          user = session['email']
          signup_out = "Sign Out"

        return render_template('fl_search_results.html',
                                searched_phrase=searched_phrase,
                                search_type=search_type,
                                num_results=num_results,
                                search_result_file_list=search_result_file_list,
                                search_result_image_list=search_result_image_list,
                                user=user, signup_out = signup_out, form=form)

    elif request.method == 'GET':
        return render_template('fl_query.html', form=form)


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

    if not os.path.exists(outfile_dir):
        subprocess.check_output("mkdir " + outfile_dir, shell=True)
    subprocess.check_output("touch " + outfile, shell=True)
    for dfxml_file in os.listdir(image_dir):
        if dfxml_file.endswith("_dfxml.xml"):
            file_list_cmd ="cd "+ image_dir + "; rm -rf tempdir; mkdir tempdir; " + "grep '\<filename\>' " + dfxml_file + " > tempdir/file1; sed \'s/<filename>//g\' tempdir/file1 > tempdir/file2; sed \'s/<\/filename>//g\' tempdir/file2 > tempdir/file3;"

            try:
                subprocess.check_output(file_list_cmd, shell=True)
            except subprocess.CalledProcessError as cmdexcept:
                logging.debug('file_list_cmd failed. Error return code: %s', cmdexcept.returncode)
                logging.debug('file_list_cmd failed. Error return output: %s', cmdexcept.output)

            cat_cmd =  "cat " + image_dir + "/tempdir/file3 >> " + outfile
            subprocess.check_output(cat_cmd, shell=True)

    return os.path.dirname(outfile)

def bcawSetIndexFlag(image_index, img):
    """ This routine sets the index flag in the image matrix, for the image
        corresponding to the given image_index.
    """

    # Get the index info from the DB:
    indexed = bcaw_db.bcawDbGetIndexFlagForImage(img)
    if not indexed:
        indexed_string = "False"
    else:
        indexed_string = "True"

    for img_tbl_item in image_matrix:
        if img_tbl_item['img_index'] == image_index:
            img_tbl_item.update({bcaw_imginfo[4]:indexed_string})
            break

@celery.task
def bcawIsImageIndexed(img):
    """ A flag to tell if an image is indexed, is maintained in the global image
        matrix. This routine checks this flag in the matrix
    """
    for img_tbl_item in image_matrix:
        if img_tbl_item['img_name'] == img:
            return img_tbl_item['index_exists']
    else:
        logging.debug('>> [bcawIsImageIndexed]: Image %s not found in the matrix', img)
        return False #FIXME

def bcawIsImageIndexedInDb(img):
    """ A flag to tell if an image is indexed, is maintained in the image table of
        the bcaw_db database. This flag should be in sync with the one in the image
        matrix. The reason it is replicated in the db is that it needs to be persistent
        between application's running and retunning.
    """
    indexed =  bcaw_db.bcawDbGetIndexFlagForImage(img)
    if not indexed:
        return False
    else:
        return True

def bcawClearIndexing():
    """ This cleans up the directory contents where lucene index is stored,
        and also clears the flags in both the database (bcaw_images) and the
        image matrix
    """
    rmcmd = "cd "+ indexDir + ";" + "rm -rf *"
    if os.path.exists(indexDir):
        logging.debug('[D]: Executing psql cmd: %s', rmcmd)
        logging.debug('>> Warning: Deleting all index files in directory %s', indexDir)
        subprocess.check_output(rmcmd, shell=True, stderr=subprocess.STDOUT)

    # If the indexing flags are set in the db and in img matrix, clear them.
    for img in os.listdir(image_dir):
        if bcaw_is_imgtype_supported(img):
            # Clear the flag in the matrix first
            bcawSetFlagInMatrix('img_index', False, img)

            # Clear the flag in the Db now
            if bcawIsImageIndexedInDb(img) == True:
                bcaw_db.bcawSetIndexForImageInDb(img, False)

def bcawSetFlagInMatrix(flag, value, image_name):
    """ This routine sets the given flag (in bcaw_imginfo) to the given value,
        in the image matrix, for all the images present.
    """
    i = 0
    for img_tbl_item in image_matrix:
        if flag == 'img_index':
            if img_tbl_item['img_name'] == image_name:
                img_tbl_item.update({bcaw_imginfo[4]:value})
                break

        elif flag == 'img_db_exists':
            # Set img_db_exists to the given value for every image in the image_table
            if img_tbl_item['img_name'] == image_name:
                img_tbl_item.update({bcaw_imginfo[2]:value})
                img_tbl_item.update({bcaw_imginfo[1]:image_name})
                break
            else:
                # Update the flag for all images
                img_tbl_item.update({bcaw_imginfo[2]:value})

        elif flag == 'dfxml_db_exists':
            # Set dfxml_db_exists to the given value for every image in the image_table
            if img_tbl_item['img_name'] == image_name:
                img_tbl_item.update({bcaw_imginfo[3]:value})
                img_tbl_item.update({bcaw_imginfo[1]:image_name})
                break
            else:
                # Update the flag for all images
                img_tbl_item.update({bcaw_imginfo[3]:value})

        i += 1
    return

def bcawUpdateMatrixWithDfxmlFlagsFromDbForAllImages():
    """ This routine updates the matrix with dfxml-table-exists flag from the DB
        for all the images present.
    """
    for img_tbl_item in image_matrix:
        img = img_tbl_item['img_name']
        ret, ret_msg = bcaw_db.dbu_execute_dbcmd("bcaw_dfxmlinfo", \
                           "find_dfxml_table_for_image", img)
        if ret != -1:
            # update the flag with True
            img_tbl_item.update({bcaw_imginfo[3]:True})

def bcawUpdateMatrixWithImageFlagsFromDbForAllImages():
    """ This routine updates the matrix with image-table-exists flag from the DB
        for all the images present.
    """
    for img_tbl_item in image_matrix:
        img = img_tbl_item['img_name']
        ret, ret_msg = bcaw_db.dbu_execute_dbcmd("bcaw_images", \
                           "find_image_table_for_image", img)
        if ret != -1:
            # update the flag with True
            img_tbl_item.update({bcaw_imginfo[2]:True})

def bcawUpdateMatrixWithlIndexFlagsFromDbForAllImages():
    """ This routine updates the matrix with index flag from the DB for all the
        images present.
    """
    for img_tbl_item in image_matrix:
        # First, get the index flag for this image from the db:
        img = img_tbl_item['img_name']
        indexed =  bcaw_db.bcawDbGetIndexFlagForImage(img)
        if indexed == 0:
            value = "False"
        else:
            value = "True"

        # Now update the matrix:
        img_tbl_item.update({bcaw_imginfo[4]:value})

def bcawSetFlagInMatrixPerImage(flag, value, image):
    """ This routine sets the given flag (in bcaw_imginfo) to the given value,
        in the image matrix, for the given image
    """
    i = 0
    for img_tbl_item in image_matrix:
        if image == img_tbl_item['img_name']:
            if flag == 'img_index':
                if img_tbl_item['img_index'] == image_index:
                    img_tbl_item.update({bcaw_imginfo[4]:1})
                    break

            elif flag == 'img_db_exists':
                # Set img_db_exists to the given value for every image in the image_table
                img_tbl_item.update({bcaw_imginfo[2]:value})

            elif flag == 'dfxml_db_exists':
                # Set dfxml_db_exists to the given value for every image in the image_table
                img_tbl_item.update({bcaw_imginfo[3]:value})

            i += 1
    else:
        logging.debug('>> bcawSetFlagMatrixPerImage: Image %s not found', image)

def bcawIsImgInMatrix(img):
    for img_tbl_item in image_matrix:
        if img_tbl_item['img_name'] == img:
            return True
    else:
        return False


@celery.task(bind=True)
def bcawIndexAllFiles(self, task_id):
    """ This routine generates Lucene indexes for all the files contained in
        the images in the disk_image directory. It is called by Celery worker
        task, which runs the job asynchronously.
        Per blog miguelgrinberg.com/post/using-celery-with-flask, using "bind=True"
        argument in the Celery decorator instructs Celery to send a self argument
        to the function, which can then be used to record the status updates
        We need task_id to send status updates from the task.
    """
    global image_list
    global image_db_list
    global partition_in
    global image_dir

    # First, create the directory FILES_TO_INDEX_DIR if doesn't exist
    files_to_index_dir = app.config['FILES_TO_INDEX_DIR']
    if not os.path.exists(files_to_index_dir):
        cmd = "mkdir " + files_to_index_dir
        subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT)

    image_index = 0
    for img in os.listdir(image_dir):
        if bcaw_is_imgtype_supported(img):
            logging.debug(">> Building Index for image: ", img)

            # Change the new files_to_index_directory into the one per image
            files_to_index_dir_per_img = files_to_index_dir + "/" + str(image_index)

            cmd = "mkdir " + files_to_index_dir_per_img
            if not os.path.exists(files_to_index_dir_per_img):
                subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT)

            ## Worker task-related code:
            ## The worker task's context will not have the following resources
            ## even though the main app has already created them. We have to
            ## create them on the worker task's context. So the following code
            ## is repeated here.
            dm = bcaw()
            image_path = image_dir+'/'+img
            dm.num_partitions = dm.bcawGetPartInfoForImage(image_path, image_index)
            image_list.append(img)
            partition_in[img] = dm.num_partitions

            idb = bcaw_db.BcawImages.query.filter_by(image_name=img).first()
            image_db_list.append(idb)
            ## END Worker-task related code

            # If index exists for this image, don't do it
            # FIXME: Query lucene to check the existance of indexing for this
            # image and continue to the next image if indexing exiss for this img.
            # Code needs to be added.
            if bcawIsImageIndexedInDb(img) == True:
                continue

            # If user has chosen not to build index for this image, skip it.
            # FIXME: Add code here

            dm = bcaw()
            image_path = image_dir+'/'+img

            logging.debug('bcawIndexAllFiles: parts %s', partition_in[img])
            temp_root_dir = "/var/www/bcaw"
            for p in range(0, partition_in[img]):
                # make the directory for this img and partition
                part_dir = str(temp_root_dir) + '/img'+str(image_index)+"_"+ str(p)


                file_list_root, fs = dm.bcawGenFileList(image_path, image_index,int(p), '/')
                if file_list_root == None:
                    print "Error: File_list_root is None for image_path {} amd part {}".format(image_path, p)
                    continue

                bcawDnldRepo(img, file_list_root, fs, image_index, p, image_path, '/')

            # If successfully indexed, set the flag to "indexed" in the image table
            # First set the index flag in the DB
            indexed = bcaw_db.bcawDbGetIndexFlagForImage(img)

            bcaw_db.bcawSetIndexForImageInDb(img, True)

            # Now Set the index flag in the matrix
            bcawSetIndexFlag(image_index, img)

            image_index += 1
            message = "Indexing in Progress"

            # Send and update_state. It can be chosen to send at particular intervals.
            # Here it is chosen to send update after indexing each image. This could
            # be changed.

            self.update_state(state='PROGRESS', \
                              task_id=task_id, \
                              meta={'current': image_index, 'status':message})

@app.route('/admin', methods=['GET', 'POST'])
def admin():
  form = adminForm()
  if request.method == 'POST':
    db_option = 3
    db_option_msg = None
    option_msg = ""
    option_msg_with_url = ""
    server_host_name = app.config['SERVER_HOST_NAME']

    # option_message could be just a message or a url. We flag the latter case:
    is_option_msg_url = False

    if (form.radio_option.data.lower() == 'all_tables'):
        logging.debug('>> Admin: Requested all tables build')
        db_option = 1
        db_option_msg = "Building All the Tables"

        # Add Tables - either image table, or DFXML table or both - to the DB
        # based on the arguments.
        task = bcaw_celery_task.bcawBuildAllTablesAsynchronously.delay()
        logging.debug("Celery: The tables will be built asynchronously")

        ##retval, db_option_msg = bcaw_db.dbBuildDb(bld_imgdb = True, bld_dfxmldb = True)
        # Task status
        task_type = "Build_all_tables"
        task_id_table['Build_all_tables'] = task.id
        db_option = 2
        db_option_msg = url_for('taskstatus', task_type='Build_all_tables')
        is_option_msg_url = True
        option_msg_with_url = "The Tables are being built. Click to see status: "
    elif(form.radio_option.data.lower() == 'image_table'):
        logging.debug('>> Admin: Requested Image table build')
        # First check if the particular image exists. If it does, don't build
        # another entry for the same image.
        # NOTE: db_option is not really used at this time. Just keeping it in
        # case it could be of use in the future. Will be removed while cleaning up,
        # if not used.
        db_option = 3
        retval, db_option_msg = bcaw_db.dbBuildDb(task_id=None, bld_imgdb = True, bld_dfxmldb = False)
    elif (form.radio_option.data.lower() == 'dfxml_table'):
        logging.debug('>> Admin: Requested DFXML table build')
        db_option = 4
        task = bcaw_celery_task.bcawBuildDfxmlTableAsynchronously.delay()
        logging.debug("Celery: DFXML table will be built asynchronously")

        db_option_msg = "DFXML Table being built"

        # Task status
        task_type = "Build_dfxml_tables"
        task_id_table['Build_dfxml_tables'] = task.id
        db_option_msg = url_for('taskstatus', task_type='Build_dfxml_tables')
        is_option_msg_url = True
        option_msg_with_url = "DFXML Table being built. Click to see status: "

    elif (form.radio_option.data.lower() == 'drop_all_tables'):
        logging.debug('>> Admin: Requested Image and DFXML DB Drop')
        db_option = 5
        retval_img, message_img = bcaw_db.dbu_drop_table("bcaw_images")

        # update the image_matrix
        bcawSetFlagInMatrix('img_db_exists', False, None)

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
        logging.debug('>> Admin Requested Image DB Drop')
        db_option = 6
        retval, db_option_msg = bcaw_db.dbu_drop_table("bcaw_images")

        # update the image_matrix
        bcawSetFlagInMatrix('img_db_exists', False, None)

    elif (form.radio_option.data.lower() == 'drop_dfxml_table'):
        logging.debug('>> Admin: Requested DFXML DB Drop')
        db_option = 7
        retval, db_option_msg = bcaw_db.dbu_drop_table("bcaw_dfxmlinfo")

        # update the image_matrix
        bcawSetFlagInMatrix('dfxml_db_exists', False, None)

    elif (form.radio_option.data.lower() == 'generate_index'):
        # First biuld the index for th filenames. Then build the index
        # for the contents from the configured directory. The contents index
        # is built in
        db_option = 8

        # Indexing needs the image_table to be present in the bca_db for every image.
        # If not present, don't start indexing.
        for img_tbl_item in image_matrix:
            img = img_tbl_item['img_name']
            ret, ret_msg = bcaw_db.dbu_execute_dbcmd("bcaw_images", \
                           "find_image_table_for_image", img)
            if ret < 0:
                db_option_msg = "Build Image Tables first. Index NOT built"
                return render_template('fl_admin_results.html',
                           db_option=str(db_option),
                           is_option_msg_url = False,
                           db_option_msg=str(db_option_msg),
                           option_msg=option_msg,
                           option_msg_with_url=option_msg_with_url,
                           form=form)

        dirFileNamesToIndex = bcaw_generate_file_list()

        # Index the filenames first
        if os.path.exists(dirFileNamesToIndex):
            index_dir = app.config['FILENAME_INDEXDIR']
            bcaw_index.IndexFiles(dirFileNamesToIndex, index_dir)
            logging.debug('>> Filename Index built in directory: %s', index_dir)
            db_option_msg = "Index built"

        # Now build the indexes for the content files fromn directory files_to-index
        # In order to not hold the browser till the indexing is done, we use
        # Celery package to offload the task to an asynchronous worker task,
        # which is run in parallel with the app.

        # First get the files starting from the root, for each image listed
        print "Celery: calling async function: "
        task = bcaw_celery_task.bcawIndexAsynchronously.apply_async()
        logging.debug("Celery: Index will be starting asynchronously: task:%s ", task)

        # FIXME: Get the return code from bcawIndexAllFiles to set db_option_msg.
        # Till now, we will assume success.
        '''
        option_msg_with_url = "The search index is being generated. This may take some time; you may navigate back to the main page and continue browsing. Click to see status: "
        '''
        option_msg = "The search index is being generated. This may take some time; you may navigate back to the main page and continue browsing. "
        option_msg_with_url = "Click here to see "

        if os.path.exists(dirFilesToIndex) :
            logging.debug('>> Building Indexes for contents in %s', dirFilesToIndex)
            bcaw_index.IndexFiles(dirFilesToIndex, indexDir)
            logging.debug('>> Built indexes for contents in %s', indexDir)

        # NOTE: Miguel's blog uses the following, which didn't make sense here.
        # Keeping the code in case it makes sense at a later time.
        # We embed the url for status in db_option_msg, which forms the link in the
        # results html output. Clicling on it invokes the routine taskstatus, which
        # sends the current status to the client in the form of a dictionary (jsonified
        # response).  We can build a user-friendly display usin that information.
        #return jsonify({}), 202, {'Location': url_for('taskstatus', task_id=task.id)}
        task_type = "Indexing"
        task_id_table['Indexing'] = task.id
        db_option = 9
        db_option_msg = url_for('taskstatus', task_type='Indexing')
        is_option_msg_url = True

    elif (form.radio_option.data.lower() == "clear_index"):
        bcawClearIndexing()
        db_option = 10
        db_option_msg = "Index Cleared "

    elif (form.radio_option.data.lower() == 'show_image_matrix'):
        db_option = 11
        db_option_msg = "Image Matrix "
        # Send the image list to the template

        # Since the asynchronous worker task which does indexing has no access
        # to the matrix, we will extract the index flags from the DB here, and
        # update the matrix before displaying.
        bcawUpdateMatrixWithlIndexFlagsFromDbForAllImages()

        # for the same reason we will also extract the dfxml flag from the db.
        bcawUpdateMatrixWithDfxmlFlagsFromDbForAllImages()
        bcawUpdateMatrixWithImageFlagsFromDbForAllImages()

        return render_template('fl_admin_imgmatrix.html',
                           db_option=str(db_option),
                           db_option_msg=str(db_option_msg),
                           image_matrix=image_matrix,
                           is_option_msg_url = is_option_msg_url,
                           form=form)
    elif (form.radio_option.data.lower() == 'show_task_status'):
        db_option = 12
        is_option_msg_url = True
        db_option_msg = url_for('bcawCheckAllTaskStatus')

    # request.form will be in the form:
    # ImmutableMultiDict([('delete_table, <image>), ), )'delete_form', 'submit')])
    # We need the image name from this dict. So we use the first element of the
    # list to get the image name so we know which image DB the table is being added
    # to or deleted from.
    bld_list = request.form.getlist('build_table')
    delete_list = request.form.getlist('delete_table')

    checked_build = 'build_table' in request.form
    checked_delete = 'delete_table' in request.form
    checked_index = 'build_index' in request.form

    if checked_build or checked_delete:

        if checked_build == True and checked_delete == True:
            db_option_msg = "Invalid combination of checked boxes"
        elif checked_build == True:
            logging.debug('D: Checked build: build_table_list: %s', bld_list[0])
            image_name = bld_list[0]

            if bld_list[0] == 'submit':
                # This means no image is selected.
                logging.debug('>> No image selected. Returning')
                db_option_msg = "Error: No Image Selected"
            elif bcaw_db.dbu_does_table_exist_for_img(image_name, 'bcaw_dfxmlinfo'):
                # First check if the dfxml table entry exists for this image.
                logging.debug('>> Table bcaw_dfxmlinfo already exists in DB')
                db_option_msg = "Table bcaw_dfxmlinfo already exists for image " + image_name
            else:
                logging.debug('>> Building DFXML table for image %s', image_name)
                retval, db_option_msg = bcaw_db.dbBuildTableForImage(image_name, bld_imgdb = False, bld_dfxmldb = True)
                if retval == 0:
                    db_option_msg = "Built DFXML Table"
        elif checked_delete == True:
            logging.debug('D: delete_table_list: %s', delete_list[0])
            image_name = delete_list[0]

            if delete_list[0] == 'submit':
                # This means no image is selected.
                logging.debug('>> No image selected. Returning')
                db_option_msg = "Error: No Image Selected"
            elif not bcaw_db.dbu_does_table_exist_for_img(image_name, 'bcaw_dfxmlinfo'):
                # First check if the dfxml table entry exists for this image.
                logging.debug('>> Table bcaw_dfxmlinfo does not exist in the DB')
                db_option_msg = "Table bcaw_dfxmlinfo does not exist for image " + image_name
            else:
                logging.debug('>> Deleting Entries for image %s from the dfxml table', image_name)
                retval, db_option_msg = \
                   bcaw_db.dbu_execute_dbcmd("bcaw_dfxmlinfo", "delete_entries_for_image", image_name)

    return render_template('fl_admin_results.html',
                           db_option=str(db_option),
                           is_option_msg_url = is_option_msg_url,
                           db_option_msg=str(db_option_msg),
                           option_msg=option_msg,
                           option_msg_with_url=option_msg_with_url,
                           form=form)

  elif request.method == 'GET':
    return render_template('fl_admin.html', form=form)

  if 'email' not in session:
    return redirect(url_for('admin'))

  user = User.query.filter_by(email = session['email']).first()

@app.route('/status/')
def bcawCheckAllTaskStatus():
    """ This routine is called when one clicks on "task status" url which
        is generated either when a celery task is run or when one clicks on
        "Show Task Status" in the admin menu.
    """
    for task_type in task_id_table:
        task_id = task_id_table[task_type]
        if task_id == 0:
            # No task exists. Return appropriate response.
            task_response_table[task_type] = {
                'state': 'None',
                'status': 'None',
            }
            continue
        task =  bcaw_celery_task.bcawIndexAsynchronously.AsyncResult(task_id)
        if task == None:
            task_response_table[task_type] = {
                'state': "No Task Running",
                'status': 'None...'
            }
            continue
        if task.state == 'PENDING':
            task_response_table[task_type] = {
                'state': task.state,
                'status': 'Pending...'
            }
        elif task.state != 'FAILURE':
            if task.state == 'SUCCESS':
                # Job is completed. No need to probe task.
                task_response_table[task_type] = {
                    'state': 'SUCCESS',
                    'status': 'TASK COMPLETED'
                }
            else:
                task_response_table[task_type] = {
                    'state': task.state,
                    'status': task.info.get('status', '')
                }
                #FIXME: Figure out how to get this into the table
                if 'result' in task.info:
                    print "[D]: Result is in taskinfo: ", task.info['result']
                    response['result'] = task.info['result']
        else:
            print ">> taskstatus: Something went wrong ", task.state
            # something went wrong in the background job
            task_response_table[task_type] = {
                'state': 'FAILURE',
                'status': str(task.info),  # this is the exception raised
            }

    return render_template('fl_celery_allstatus.html', \
                           task_id_table=task_id_table,
                           task_response_table=task_response_table)

@app.route('/status/<task_type>')
def taskstatus(task_type):
    """ The routine that runs when clicked on the status URL for the corresponding
        task ID.
    """
    task_id = task_id_table[task_type]
    if task_id == 0:
        # No task exists. Return appropriate response.
        response = {
            'state': 'None',
            'status': 'None',
        }
        return render_template('fl_celery_status.html', \
                                   response=response, \
                                   task_type=task_type)

    task =  bcaw_celery_task.bcawIndexAsynchronously.AsyncResult(task_id)
    if task == None:
        response = {
            'state': "No Task Running",
            'status': 'None...'
        }
        return render_template('fl_celery_status.html', \
                               response=response, \
                               task_type=task_type)

    print "[D]: In taskstatus: task_state: ", task.state
    if task.state == 'PENDING':
        response = {
            'state': task.state,
            'status': 'Pending...'
        }
    elif task.state != 'FAILURE':
        if task.state == 'SUCCESS':
            # Job is completed. No need to probe task.
            response = {
                'state': 'SUCCESS',
                'status': 'TASK COMPLETED'
            }
        else:
            response = {
                'state': task.state,
                'status': task.info.get('status', '')
            }
            if 'result' in task.info:
                print "[D]: Result is in taskinfo: ", task.info['result']
                response['result'] = task.info['result']
    else:
        print ">> taskstatus: Something went wrong ", task.state
        # something went wrong in the background job
        response = {
            'state': 'FAILURE',
            'status': str(task.info),  # this is the exception raised
        }
    print "[D] response: ", response
    return render_template('fl_celery_status.html', \
                           response=response, \
                           task_type=task_type)

# FIXME: This is never called (since we run runserver.py)
# Remove once confirmed to be deleted
if __name__ == "__main__":
    dm = bcaw()
    bcaw_db.bcawdb()
    app.run()
