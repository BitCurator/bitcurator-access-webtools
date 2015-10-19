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
# This file is part of the BitCurator Access Webtools application.
# Code is used from the samples provided in Lucene download package.
# It provides routines to index the given text files and to search for
# a specified string using these indexes.
#
INDEX_DIR = "IndexFiles.index"

import sys, os, lucene, threading, time
from datetime import datetime
import subprocess
from subprocess import Popen,PIPE

from java.io import File
from org.apache.lucene.analysis.miscellaneous import LimitTokenCountAnalyzer
from org.apache.lucene.analysis.standard import StandardAnalyzer
from org.apache.lucene.document import Document, Field, FieldType
from org.apache.lucene.index import FieldInfo, IndexWriter, IndexWriterConfig
from org.apache.lucene.store import SimpleFSDirectory
from org.apache.lucene.util import Version
from org.apache.lucene.queryparser.classic import QueryParser

class IndexFiles(object):
    """ IndexFiles takes the root of a directory structure and the destination
        directory as arguments to create Lucene indexes for the directory 
        and copy the indexs into the target directory. 
        Attributes:
        root: Root of the directory structure containing files to be indexed.
        store_dir: Output directory where indexes are to be stored. 
    """
    def __init__(self, root, store_dir):

        if not os.path.exists(store_dir):
            os.mkdir(store_dir)

        # NOTE: Hardcoded the analyzer instead of passing it
        lucene.initVM()
        '''
        vm_env = lucene.getVMEnv()
        vm_env.attachCurrentThread()
        '''
        analyzer = StandardAnalyzer(Version.LUCENE_CURRENT)
        store = SimpleFSDirectory(File(store_dir))
        analyzer = LimitTokenCountAnalyzer(analyzer, 1048576)
        config = IndexWriterConfig(Version.LUCENE_CURRENT, analyzer)

        # setting CREATE will rewrite over the existing indexes.
        ###config.setOpenMode(IndexWriterConfig.OpenMode.CREATE)

        writer = IndexWriter(store, config)

        self.indexDocs(root, writer)
        writer.close()

    def indexDocs(self, root, writer):

        # t1 is used for filenames and t2 is used for contents
        t1 = FieldType()
        t1.setIndexed(True)
        t1.setStored(True)
        t1.setTokenized(False)
        t1.setIndexOptions(FieldInfo.IndexOptions.DOCS_AND_FREQS)

        t2 = FieldType()
        t2.setIndexed(True)
        t2.setStored(False)
        t2.setTokenized(True)
        t2.setIndexOptions(FieldInfo.IndexOptions.DOCS_AND_FREQS_AND_POSITIONS)

        ## print("D1: indexDocs:root: ", root)
        for root, dirnames, filenames in os.walk(root):
            for filename in filenames:
                # We can index only a certain types of files
                if not (filename.endswith('.txt') or filename.endswith('.pdf') or filename.endswith('.xml') or filename.endswith('.doc')):
                    continue
                try:
                    file_path = os.path.join(root, filename)
                    outfile_path = file_path

                    # First convert PDF and DOC files to text
                    if filename.endswith('.pdf'):
                        ## print "D2: indexDocs: It Is a PDF file" , filename
                        outfile = filename.replace('.pdf', '.txt')
                        outfile_path = os.path.join(root, outfile)
                        cmd = 'pdftotext ' + '-layout ' + "'"+ file_path +  "'" + ' ' + "'" + outfile_path + "'" 
                        ## print "D1: indexDocs: pdftotext Command: ", cmd
                        subprocess.check_output(cmd, shell=True)
                        file_path = outfile_path
                    elif filename.endswith('.doc'):
                        ## print "D2: indexDocs: It Is a .DOC file" , filename
                        outfile = filename.replace('.doc', '.txt')
                        outfile_path = os.path.join(root, outfile)
                        cmd = 'antiword ' +  file_path + ' >> ' + outfile_path
                        ## print "D1: indexDocs: antiword Command: ", cmd
                        subprocess.check_output(cmd, shell=True)
                        file_path = outfile_path

                    file = open(file_path)
                    contents = unicode(file.read(), 'iso-8859-1')
                    file.close()
                    doc = Document()
                    doc.add(Field("name", filename, t1))
                    doc.add(Field("path", root, t1))
                    if len(contents) > 0:
                        doc.add(Field("contents", contents, t2))
                    else:
                        print "warning: no content in %s" % filename
                    writer.addDocument(doc)
                    ## print "indexDocs: Added Document for ", filename
                except Exception, e:
                    print "Failed in indexDocs:", e

def searchIndexedFiles(searcher, analyzer, search_text):
    """ Searces the Lucene index created by indexDocs for the given string,
        search_text
    """
    search_list = []
    print "Searching for:", search_text
    query = QueryParser(Version.LUCENE_CURRENT, "contents",
                        analyzer).parse(search_text)
    scoreDocs = searcher.search(query, 50).scoreDocs
    print "%s total matching documents." % len(scoreDocs)

    if len(scoreDocs) == 0:
        print "Query: Not found for : ",search_text
        return None
    else:
        for scoreDoc in scoreDocs:
            doc = searcher.doc(scoreDoc.doc)
            ## print 'D: searchIndexedFiles: path:', doc.get("path"), 'name:', doc.get("name")
            file_path = doc.get("path") + "/" + doc.get("name")
            search_list.append(file_path)
        ## print "D: searchIndexFiles: Search List from Lucene Indexing ", search_list
        return search_list
