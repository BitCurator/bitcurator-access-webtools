#!/usr/bin/python
# coding=UTF-8
#
# BitCurator Access Webtools (Disk Image Access for the Web)
# Copyright (C) 2014 - 2023
# All rights reserved.
#
# This code is distributed under the terms of the GNU General Public
# License, Version 3. See the text file "COPYING" for further details
# about the terms of this license.
#
"""Classes for full text indexing, search and retrieval using Lucene."""
import os
import logging
import lucene
from textract import process
from textract.exceptions import ExtensionNotSupported

from java.nio.file import Paths
from org.apache.lucene.analysis.miscellaneous import LimitTokenCountAnalyzer
from org.apache.lucene.analysis.standard import StandardAnalyzer
from org.apache.lucene.document import Document, Field, FieldType
from org.apache.lucene.index import IndexWriter, IndexWriterConfig, IndexOptions
from org.apache.lucene.index import DirectoryReader, Term
from org.apache.lucene.store import SimpleFSDirectory
from org.apache.lucene.search import IndexSearcher
from org.apache.lucene.queryparser.classic import QueryParser

from .model import ByteSequence
from .utilities import MimeMapper, map_mime_to_ext

lucene.initVM(vmargs=['-Djava.awt.headless=true'])

MIME_MAPPER = MimeMapper()

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

    mime_map = MimeMapper("/var/www/bcaw/conf/mimemap.conf")

    def __init__(self, store_dir):
        self.store_dir = store_dir
        if not os.path.exists(store_dir):
            os.mkdir(store_dir, 0o777)
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

    @classmethod
    def get_path_details(cls, temp_path, image_path):
        """Return the byte sequence and the full text for a given path."""
        byte_sequence = ByteSequence.from_path(temp_path)
        extension = map_mime_to_ext(byte_sequence.mime_type, cls.mime_map)
        logging.debug("Assessing MIME: %s EXTENSION %s SHA1:%s", byte_sequence.mime_type,
                      extension, byte_sequence.sha1)
        full_text = ""
        if extension is not None:
            try:
                logging.debug("Textract for SHA1 %s, extension map val %s",
                              byte_sequence.sha1, extension)
                full_text = process(temp_path, extension=extension, encoding='ascii',
                                    preserveLineBreaks=True)
            except ExtensionNotSupported as _:
                logging.exception("Textract extension not supported for ext %s", extension)
                logging.debug("Image path for file is %s, temp file at %s", image_path, temp_path)
                full_text = "N/A"
            except LookupError as _:
                logging.exception("Lookup error for encoding.")
                logging.debug("Image path for file is %s, temp file at %s", image_path, temp_path)
                full_text = "N/A"
            except UnicodeDecodeError as _:
                logging.exception("UnicodeDecodeError, problem with file encoding")
                logging.debug("Image path for file is %s, temp file at %s", image_path, temp_path)
                full_text = "N/A"
            except:
                logging.exception("Textract UNEXPECTEDLY failed for temp_file.")
                logging.debug("Image path for file is %s, temp file at %s", image_path, temp_path)
                full_text = "N/A"
        return byte_sequence, full_text

    def index_path(self, temp_path, image_path):
        """Index the full text of the file and map it to the file's sha1 and return
        the derived ByteStream object and derived full text as a tuple."""
        byte_sequence, full_text = self.get_path_details(temp_path, image_path)
        if full_text:
            self.index_text(byte_sequence.sha1, full_text)
        return byte_sequence, full_text

class FullTextSearcher(object):
    """Performs Lucene searches."""
    max_results = 1000
    def __init__(self, store_dir):
        self.store_dir = store_dir
        if not os.path.exists(store_dir):
            os.mkdir(store_dir, 0o777)
        self.store = SimpleFSDirectory(Paths.get(store_dir))
        self.searcher = None
        self.analyzer = StandardAnalyzer()
        self.analyzer = LimitTokenCountAnalyzer(self.analyzer, 1048576)

    def __enter__(self):
        try:
            if self.searcher is None:
                self.searcher = IndexSearcher(DirectoryReader.open(self.store))
        except lucene.JavaError as _je:
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
        if text and self.searcher:
            query = QueryParser("full_text", self.analyzer).parse(text)
            hits = self.searcher.search(query, FullTextSearcher.max_results)
            result_dict = {}
            for hit in hits.scoreDocs:
                doc = self.searcher.doc(hit.doc)
                result_dict[doc.get('sha1')] = hit.score
        return result_dict
