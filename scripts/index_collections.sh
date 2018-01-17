#!/usr/bin/env bash
# Set directory to install dir, this should be templated
cd /var/www/bcaw
# activate the virtual env
source venv/bin/activate
# Set config format to disable logging debug, comment out for full logging
export BCAW_CONFIG='analyser'
# Run the analyser
python -m bcaw.image_analyser
