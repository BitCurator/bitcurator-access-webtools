DIMAC: Disk Image Access for the Web
------------------------------------
DIMAC is a digital media access tool geared towards the needs of archives and libraries. DIMAC
provides simple access to disk images over the web using open source technologies including
The Sleuth Kit, PyTSK, and Flask. Simply point DIMAC at a local directory that contains raw (dd)
or forensically-packaged disk images, and it will create a web portal that allows you to browse
the file systems, download files, and examine disk image metadata.

<http://wiki.bitcurator.net/dimac>

# Getting started
To check out the DIMAC code repo, run:

* git clone https://github.com/kamwoods/dimac

Running the sample program is easy. First, you'll need to tell the Flask application where the directory containing your disk images is.

* cd dimac/dimac

Now, edit image\_browse.py and change the image\_dir directory to the appropriate directory on your host. Now:

* cd ../
* python runserver.py

Now, open a web browser and navigate to 127.0.0.1:5000

# Dependencies

DIMAC is a Flask app. It has been tested with Python 2.7.3, Flask 0.11, Jinja2, and Postgres 9.1 (but will likely work with other versions). If you're unsure whether you have the correct dependencies, see the "Dependencies" section below.

On a Debian or Ubuntu system, fulfilling these dependencies is easy. Just run the following commands to install python-pip and flask:

* sudo apt-get install python-pip
* sudo pip install flask

In order to use the database backend, you'll also need postgresql. On a Ubuntu or Debian system, you can install this with the following command:

* sudo apt-get install postgresql

PGAdmin 3 will simplify the process of managing databases you may use with the application. You can install this with:

* sudo apt-get install pgadmin3

In order to build server-side applications (and configure psycopg2 for use by the Flask app) you'll need the postgresql server development package:

* sudo apt-get install postgresql-server-dev-9.1

You'll also need psycopg2 and SQLAlchemy to run the app:

* sudo pip install -U psycopq2
* sudo pip install Flask-SQLAlchemy

(More coming soon)

# DIMAC Documentation

Coming soon...
[http://wiki.bitcurator.net/dimac](http://wiki.bitcurator.net/dimac).

# License(s)

DIMAC project documentation, and other non-software products of the DIMAC team are subject to the the Creative Commons Attribution 3.0 Unported license (CC BY 3.0).

Unless otherwise indicated, software objects in this repository are distributed under the terms of the GNU General Public License, Version 3. See the text file "COPYING" for further details about the terms of this license.


