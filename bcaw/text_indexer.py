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
    """Given an image details the indexer will get all text files, lucene them
    for search and retrieval."""
    hash_field = FieldType()
    hash_field.setStored(True)
    hash_field.setTokenized(False)
    hash_field.setIndexOptions(IndexOptions.DOCS_AND_FREQS)

    text_field = FieldType()
    text_field.setStored(False)
    text_field.setTokenized(True)
    text_field.setIndexOptions(IndexOptions.DOCS_AND_FREQS_AND_POSITIONS)

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

class FullTextSearcher(object):
    """Performs Lucene searches."""
    max_results = 1000
    def __init__(self, store_dir):
        self.store_dir = store_dir
        if not os.path.exists(store_dir):
            os.mkdir(store_dir, 0777)
        self.store = SimpleFSDirectory(Paths.get(store_dir))
        self.searcher = None
        self.analyzer = StandardAnalyzer()
        self.analyzer = LimitTokenCountAnalyzer(self.analyzer, 1048576)

    def __enter__(self):
        try:
            if self.searcher is None:
                self.searcher = IndexSearcher(DirectoryReader.open(self.store))
        except lucene.JavaError, _je:
            logging.exception("No Lucene index found at %s", self.store)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self.searcher is not None:
            del self.searcher
            self.searcher = None

    def retrieve(self, text):
        """Search the Lucene index for a text term."""
        result_dict = {}
        if not text:
            return result_dict

        text = text.strip()
        if text:
            query = QueryParser("full_text", self.analyzer).parse(text)
            hits = self.searcher.search(query, FullTextSearcher.max_results)
            result_dict = {}
            for hit in hits.scoreDocs:
                doc = self.searcher.doc(hit.doc)
                result_dict[doc.get('sha1')] = hit.score
        return result_dict
