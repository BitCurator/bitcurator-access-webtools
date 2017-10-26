#!/usr/bin/env bash

cd /var/www/bcaw
source venv/bin/activate
python -m bcaw.image_analyser
