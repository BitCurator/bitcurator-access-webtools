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

  $ git clone https://github.com/kamwoods/dimac

Running the sample program is easy. First, you'll need to tell the Flask application where the directory containing your disk images is.

  $ cd dimac/dimac

Edit image\_browse.py and change the image\_dir directory to the appropriate directory on your host. Now:

  $ cd ../
  $ python runserver.py

Now, open a web browser and navigate to 127.0.0.1:5000. Of course, if you haven't installed the dependencies, below, you'll need them before you can get started.

# Dependencies

DIMAC is a Flask app. It has been tested with Python 2.7.3, Flask 0.11, Jinja2, and Postgres 9.1 (but will likely work with other versions). DIMAC will *not* currently work with Python 3.x, as the PyTSK libraries have not yet been ported.
You'll also need a range of other forensics tools, including AFFLIB (v3.7.4 or later), libewf, The Sleuth Kit, and PyTSK.

On a Debian or Ubuntu system, fulfilling the some of these dependencies is easy. Others are a bit more involved, as the required versions of the necessary packages have not yet been packaged. The instructions below should help: 

Install python-pip and Flask:
-----------------------------

  $ sudo apt-get install python-pip
  $ sudo pip install flask

In order to use the database backend, you'll also need postgresql. On a Ubuntu or Debian system, you can install this with the following command:

  $ sudo apt-get install postgresql

PGAdmin 3 will simplify the process of managing databases you may use with the application. You can install this with:

  $ sudo apt-get install pgadmin3

In order to build server-side applications (and configure psycopg2 for use by the Flask app) you'll need the postgresql server development package:

  $ sudo apt-get install postgresql-server-dev-9.1

Install psycopg2 and SQLAlchemy (required):
-------------------------------------------

  $ sudo pip install -U psycopq2
  $ sudo pip install Flask-SQLAlchemy

Set up the database:
--------------------

We need to change the PostgreSQL postgres user password; we will not be able to access the server otherwise. As the “postgres” Linux user, execute the psql command. In a terminal, type: 

  $ sudo -u postgres psql postgres

Now, in the postgres prompt, type the following:
  $ \password postgres

You’ll need to enter a password, twice, for the “postgres” (master RDBMS control) user. You won’t see the password appear as you type it (twice). Our example below assumes you use the master user "bcadmin".

Now hit “Ctrl-D” to quit the pgsql prompt.

Now, it’s time to create a new user who can create new databases but not other users (note that you won’t see the characters you type in as the password):

  $ sudo -u postgres createuser -A -P bcadmin
  $ Enter password for new role: bcadmin
  $ Enter it again: bcadmin
  $ Shall the new role be allowed to create databases? (y/n) y
  $ Shall the new role be allowed to create more new roles? (y/n) n

Now, create a new database (in this example, we'll call it “bcdb”) with user access rights for the user we created earlier (the "bcadmin" user, in this example, and the -O in the following line is a capital letter O, not a zero): 

  $ sudo -u postgres createdb -O bcadmin bcdb

Finally, do a full restart on the database, and you should be ready to go:

  $ sudo /etc/init.d/postgresql restart

Install libewf:
---------------

Download the current libewf code from the downloads link at https://code.google.com/p/libewf/. Unpack the .tar.gz file, change into the libewf directory, and run the following:

  $ ./bootstrap
  $ ./configure --enable-v1-api
  $ make
  $ sudo make install
  $ sudo ldconfig

Install The Sleuth Kit:
-----------------------

Download the current master source from http://www.sleuthkit.org/sleuthkit/download.php. (Note: There's an older version of The Sleuth Kit available as a Debian/Ubunut package. Don't use it! It's out of date!) Unpack the .tar.gz file, change into the sleuthkit directory, and run the following:

  $ ./configure

  $ make

  $ sudo make install

  $ sudo ldconfig

Install The Sleuth Kit Python bindings:
---------------------------------------

Download the current pytsk (TSK Python bindings) from https://code.google.com/p/pytsk/. Unpack the .tar.gz files, change into the pytsk directory, and run the following:

  $ python setup.py build
  $ sudo python setup.py install

(More coming soon...)

# DIMAC Documentation

Coming soon...
[http://wiki.bitcurator.net/dimac](http://wiki.bitcurator.net/dimac).

# License(s)

DIMAC project documentation, and other non-software products of the DIMAC team are subject to the the Creative Commons Attribution 3.0 Unported license (CC BY 3.0).

Unless otherwise indicated, software objects in this repository are distributed under the terms of the GNU General Public License, Version 3. See the text file "COPYING" for further details about the terms of this license.


