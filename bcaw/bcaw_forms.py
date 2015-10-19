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
# This file contains the flask forms for BitCurator Access webtools.
# Ref: http://code.tutsplus.com/tutorials/intro-to-flask-signing-in-and-out--net-29982
#

from bcaw import app
from flask.ext.wtf import Form 
from wtforms import TextField, TextAreaField, SubmitField, validators, ValidationError, PasswordField, RadioField
from bcaw_userlogin_db import User, db_login
import bcaw_db
import bcaw_index
import lucene
from org.apache.lucene.store import SimpleFSDirectory
from org.apache.lucene.search import IndexSearcher
from java.io import File
from org.apache.lucene.analysis.standard import StandardAnalyzer
from org.apache.lucene.index import DirectoryReader
from org.apache.lucene.util import Version
 
class ContactForm(Form):
  name = TextField("Name")
  email = TextField("Email")
  subject = TextField("Subject")
  message = TextAreaField("Message")
  submit = SubmitField("Send")

class SignupForm(Form):
    firstname = TextField("First name",  [validators.Required("Please enter your first name.")])
    lastname = TextField("Last name",  [validators.Required("Please enter your last name.")])
    email = TextField("Email",  [validators.Required("Please enter your email address."), validators.Email("Please enter your email address.")])
    password = PasswordField('Password', [validators.Required("Please enter a password.")])
    submit = SubmitField("Create account")
 
    def __init__(self, *args, **kwargs):
        Form.__init__(self, *args, **kwargs)
 
    def validate(self):
        if not Form.validate(self):
            return False
     
        user = User.query.filter_by(email = self.email.data.lower()).first()
        if user:
            self.email.errors.append("That email is already taken")
            return False
        else:
            return True
        return True

class SigninForm(Form):
  email = TextField("Email",  [validators.Required("Please enter your email address."), validators.Email("Please enter your email address.")])
  password = PasswordField('Password', [validators.Required("Please enter a password.")])
  submit = SubmitField("Sign In")
   
  def __init__(self, *args, **kwargs):
    Form.__init__(self, *args, **kwargs)
 
  def validate(self):
    if not Form.validate(self):
      return False
     
    user = User.query.filter_by(email = self.email.data.lower()).first()
    if user and user.check_password(self.password.data):
      return True
    else:
      self.email.errors.append("Invalid e-mail or password")
      return False

class QueryForm(Form):
    """ The search query in the home page which has a search box and a set of
        radio buttons to choose the search option: filename or contents.
        If option 'filename' is chosen, the search tries to match the search
        string with the filenames in the database. If 'contents' option is
        chosen, it searches the contents in the directory bca-webtools/files_to_index.
        (Indexes for these files are stored in bca-webtools/lucene_index

        search_text: the actual text string being searched for
        radio_option: One of the two options: filename or contents
    """
    #search_text = TextField("Search", [validators.Required("Please enter the search phrase"), validators.DataRequired("Please enter the search phrase") )
    search_text = TextField("Search" )
    radio_option = RadioField('Label', choices=[('filename', 'filename'), ('contents', 'contents')], default='contents')
    submit = SubmitField("Search")
    search_result = []
    q1 = []
    q2 = []

    print "D: Search_text: ", search_text
    print "D: Radio Option: ", radio_option

    def __init__(self, *args, **kwargs):
        Form.__init__(self, *args, **kwargs)

    def searchDfxmlDb(self):
        """ Searches the DFXML Database or the contents directory, based on
            the radio button selected, looking for the search string. 
        """

        print "D: Search_text: ", self.search_text.data.lower()
        print "D: radio_option: ", self.radio_option.data.lower()

        if not Form.validate(self):
            print("bcaw_forms: Validate failed. returning ");
            return None, self.radio_option.data.lower()

        search_text_query = '%' + self.search_text.data.lower() + '%'
        print "D: bcaw_forms: search_text_query = ", search_text_query

        # If radio_button indicates 'filename', do a filename search. 
        # Otherwise (contents), do a lucene index search
        # There are two options to do the file_name search. One is from the DB,
        # which is the default at this time. The second one is from the indexes.
        # NOTE (FIXME):
        # Currently the index is built from the list of all files. That doesn't
        # give information on the path of the file, etc. That will be addressed soon.
        if self.radio_option.data.lower() in "filename" and app.config["FILESEARCH_DB"]:
            print("D: bcaw_forms: It is a filename Search ")

            # Method#1: Using DB Query for file-name search
            # This works just fine.
            q1 = bcaw_db.BcawDfxmlInfo.query.filter(bcaw_db.BcawDfxmlInfo.fo_filename.ilike(search_text_query))
            print("D: bcaw_forms: Query: ", q1.limit(5).all())
    
            q2 = q1.all()
            if len(q2) == 0:
                print "Query: Not found: ", self.search_text.data.lower()
                return None, 'filename'
            last_elem = len(q2) - 1
            ## print "D: Length-1: ", last_elem
            return q2, "filename"
        else:
            # It could be filename search with index or content search.
            if self.radio_option.data.lower() in "filename":
                indexDir = app.config['FILE_INDEXDIR']
            else:
                indexDir = app.config['INDEX_DIR']

            print("D: BCAW: It is a Content Search: indexDir: ", indexDir)
            print 'lucene', lucene.VERSION
            #base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
            #directory = SimpleFSDirectory(File(os.path.join(base_dir, INDEX_DIR)))
  
            # The directory where the indexes are stored is a configurable option
            # and is defined in bcaw_default_settings.py

            # Start lucene VM only if it is not started yet.
            # It is started when the indexes are built. But if one tries to search
            # with indexes that are already saved in the index directory, the 
            # VM needs to be started.
            vm_env = lucene.getVMEnv()
            if vm_env == None:
                print "D: baw_forms: Sarting Lucene VM: "
                lucene.initVM()

            directory = SimpleFSDirectory(File(indexDir))
            searcher = IndexSearcher(DirectoryReader.open(directory))
            analyzer = StandardAnalyzer(Version.LUCENE_CURRENT)

            # Now search for the string in the index files created by lucene 
            search_list = bcaw_index.searchIndexedFiles(searcher, analyzer, self.search_text.data.lower())
            return search_list, "contents"
            
class adminForm(Form):
    radio_option = RadioField('Label', choices=[('Image_table', 'Build Image Table'), ('dfxml_table', 'Build DFXML Table'), ('all_tables', 'Build All Tables'), ('drop_img_table', 'Drop Image Table'), ('drop_dfxml_table', 'Drop DFXML Table'), ('drop_all_tables', 'Drop All Tables'), ('generate_index', 'Generate Index'), ('show_image_matrix','Show Image Matrix')])
    submit = SubmitField("Submit")
 
    def __init__(self, *args, **kwargs):
        Form.__init__(self, *args, **kwargs)

    def adminAction(self):
        if not Form.validate(self):
            print(">> bcaw_forms: Validate failed. returning ");
            return None, self.radio_option.data.lower()

class buildForm(Form):
    radio_option = RadioField('Label', choices=[('build_db_table', 'Build DB Table'), ('rmove_db_table', 'Remove dB Table')], default='')
    submit = SubmitField("Submit")

    def __init__(self, *args, **kwargs):
        Form.__init__(self, *args, **kwargs)

    def buildAction(self):
        if not Form.validate(self):
            print(">> bcaw_forms: Validate failed. returning ");
            return None, self.radio_option.data.lower()

