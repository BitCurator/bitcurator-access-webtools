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
# This file contains code for named entity recognition..
# Ref: http://timmcnamara.co.nz/post/2650550090/extracting-names-with-6-lines-of-python-code
#

import nltk

def extract_entities(text):
  for sent in nltk.sent_tokenize(text):
    for chunk in nltk.ne_chunk(nltk.pos_tag(nltk.word_tokenize(sent))):
      if hasattr(chunk, 'node'):
        print chunk.node, ' '.join(c[0] for c in chunk.leaves())
