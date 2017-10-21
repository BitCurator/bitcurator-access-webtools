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

import os
import logging

import lucene

from java.nio.file import Paths
from org.apache.lucene.analysis.miscellaneous import LimitTokenCountAnalyzer
from org.apache.lucene.analysis.standard import StandardAnalyzer
from org.apache.lucene.document import Document, Field, FieldType
from org.apache.lucene.index import IndexWriter, IndexWriterConfig, IndexOptions
from org.apache.lucene.index import DirectoryReader, Term
from org.apache.lucene.store import SimpleFSDirectory
from org.apache.lucene.search import IndexSearcher
from org.apache.lucene.queryparser.classic import QueryParser


lucene.initVM(vmargs=['-Djava.awt.headless=true'])

class ImageIndexer(object):
    hash_field = FieldType()
    hash_field.setStored(True)
    hash_field.setTokenized(False)
    hash_field.setIndexOptions(IndexOptions.DOCS_AND_FREQS)

    text_field = FieldType()
    text_field.setStored(False)
    text_field.setTokenized(True)
    text_field.setIndexOptions(IndexOptions.DOCS_AND_FREQS_AND_POSITIONS)

    """Given an image details the indexer will get all text files, lucene them
    for search and retrieval."""
    def __init__(self, store_dir):
        self.store_dir = store_dir
        if not os.path.exists(store_dir):
            os.mkdir(store_dir, 0777)
        self.store = SimpleFSDirectory(Paths.get(store_dir))
        self.analyzer = StandardAnalyzer()
        self.analyzer = LimitTokenCountAnalyzer(self.analyzer, 1048576)
        self.config = IndexWriterConfig(self.analyzer)
        self.writer = IndexWriter(self.store, self.config)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.writer.close()

    def index_text(self, sha1, full_text):
        """Index the full text and map it to the source sha1."""
        document = Document()
        document.add(Field("sha1", sha1, ImageIndexer.hash_field))
        if full_text:
            document.add(Field("full_text", full_text, ImageIndexer.text_field))
            self.writer.updateDocument(Term("sha1", sha1), document)
        else:
            logging.info("No text for sha1 %s", sha1)

    def retrieve(self, text):
        """Search the Lucene index for a text term."""
        try:
            searcher = IndexSearcher(DirectoryReader.open(self.store))
        except lucene.JavaError, _je:
            logging.exception("No Lucene index found at %s", self.store)
            return "No docs found"
        query = QueryParser("full_text", self.analyzer).parse(text)

        max_results = 1000
        hits = searcher.search(query, max_results)
        result_tuples = []
        for hit in hits.scoreDocs:
            doc = searcher.doc(hit.doc)
            result_tuples.append((doc.get('sha1'), hit.score))
        del searcher
        return result_tuples
