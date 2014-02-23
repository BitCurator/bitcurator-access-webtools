DIMAC: Disk Image Access for the Web
------------------------------------
<http://wiki.bitcurator.net/dimac>

# Getting started

DIMAC provides simple access to disk images over the web using open source technologies including
The Sleuth Kit, PyTSK, and Flask.

To check out the DIMAC code repo, run:

* git clone https://github.com/kamwoods/dimac

Running the sample program is easy. First, you'll need to tell the Flask application where the directory containing your disk images is.

* cd dimac/dimac

Now, edit image\_browse.py and change the image\_dir directory to the appropriate directory on your host. Now:

* cd ../
* python runserver.py

Now, open a web browser and navigate to 127.0.0.1:5000

# Dependencies

DIMAC is a Flask app. It has been tested with Python 2.7.3, Flask 0.10, and the related dependencies for Flask (including Jinja2).

On a Debian or Ubuntu system, fulfilling these dependencies is easy. Just run the following commands to install python-pip and flask:

* sudo apt-get install python-pip
* sudo pip install flask

# DIMAC Documentation

Coming soon...
[http://wiki.bitcurator.net/dimac](http://wiki.bitcurator.net/dimac).

# License(s)

DIMAC project documentation, and other non-software products of the DIMAC team are subject to the the Creative Commons Attribution 2.0 Generic license (CC By 2.0).

Unless otherwise indicated, software objects in this repository are distributed under the terms of the GNU General Public License, Version 3. See the text file "COPYING" for further details about the terms of this license.


