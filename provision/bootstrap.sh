#!/usr/bin/env bash

SCRIPT_PATH=$(dirname $(readlink -f $0 ) )

##
# Bash script to provision VM, used to set up BCA environment.
#
# Be aware this script is only the first time you issue the
#    vagrant up
# command, or following a
#    vagrant destroy
#    vagrant up
# combination.  See the README for further detais.
##

# Update and upgrade the box
sudo apt-get update -y
sudo apt-get upgrade -y

# Install subversion
sudo apt-get install subversion

# Install build-essential and autotools
sudo apt-get install -y build-essential
sudo apt-get install -y libtool
sudo apt-get install -y automake

# To pull git repos
sudo apt-get install -y git

# Bison provides yacc, needed for libewf. Also flex.
sudo apt-get install -y bison
sudo apt-get install -y flex

# Install python-dev
sudo apt-get install -y python-dev

# Install pip and flask
sudo apt-get install -y python-pip
sudo pip install flask

# Needed for libewf
sudo apt-get install -y zlib1g-dev

# Install Postgress as back end database
sudo apt-get install -y postgresql

# PGAdmin 3 for database management
sudo apt-get install -y pgadmin3

# Postgress dev package
sudo apt-get install -y postgresql-server-dev-9.3

# psycopg2 and flask SQL Alchemy
sudo pip install -U psycopg2
sudo pip install Flask-SQLAlchemy

# Flask WTForms
sudo pip install flask-wtf

# libtalloc
sudo apt-get install -y libtalloc2
sudo apt-get install -y libtalloc-dev

# Needed for text extraction
sudo apt-get install -y antiword
sudo apt-get install -y poppler-utils

# Dependencies for Python Bokeh
# See http://bokeh.pydata.org/en/latest/docs/installation.html#install-dependencies
# Some are already satsified from earlier Flask install
sudo apt-get install -y redis-server

# Minimum deps for scipy in pip
sudo apt-get install -y python python-dev libatlas-base-dev gcc gfortran g++

# Oracle Java 8 silent install
sudo apt-get -y -q install software-properties-common htop
sudo add-apt-repository -y ppa:webupd8team/java
sudo apt-get -y -q update
echo oracle-java8-installer shared/accepted-oracle-license-v1-1 select true | sudo /usr/bin/debconf-set-selections
echo oracle-java7-installer shared/accepted-oracle-license-v1-1 select true | sudo /usr/bin/debconf-set-selections
sudo apt-get -y -q install oracle-java8-installer
#apt-get -y -q install oracle-java7-installer
sudo update-java-alternatives -s java-8-oracle

# Install ant: (installs in /usr/bin/ant)
sudo apt-get install -y ant
sudo apt-get install -y ant-doc
sudo apt-get install -y ant-optional

# Install ivy
sudo apt-get install -y ivy
sudo apt-get install -y ivy-doc

# Update shared libraries
sudo ldconfig

# Install pylucene (also installs JCC)
sudo wget http://apache.mirrors.pair.com/lucene/pylucene/pylucene-4.10.1-1-src.tar.gz
tar -zxvf pylucene-4.10.1-1-src.tar.gz
cd pylucene-4.10.1-1
pushd jcc
python setup.py build
python setup.py install
popd

# Edit the Makefile to uncomment the config info for Linux.
# First we look for the requred string in the makefile and copy the 5 lines
# strting from the 4th line after the pattern match, into a temp file (temp),
# after removing the leading hash (to uncomment the lines).
# Then we append these lines from temp file to Makefile after the given pattern
# is found.
grep -A 8 "Ubuntu 11.10 64-bit" Makefile | sed -n '4,8p' | sed 's/^#//' > temp
sed -i -e '/Ubuntu 11.10 64-bit/r temp' Makefile
make
sudo make install
sudo ldconfig

# Check postgress setup
check_install postgresql postgresql

# .pgpass contains the password for the vagrant user. Needs to be in the home directory.
sudo cp /vagrant/.pgpass /home/vagrant/.pgpass

# Start postgress and setup up postgress user
sudo service postgresql start

# Create the database bca_db with owner vagrant
# Create user first
sudo -u postgres psql -c"CREATE user vagrant WITH PASSWORD 'vagrant'"

# Create the database
sudo -u postgres createdb -O vagrant bca_db

# Legacy - kept for reference
#sudo -u postgres psql -c"ALTER user postgres WITH PASSWORD 'bcadmin'"
#sudo -u postgres psql -c"CREATE user bcadmin WITH PASSWORD 'bcadmin'"
#sudo -u postgres createdb -O bcadmin bcdb

# Restart postgres
sudo service postgresql restart

# Verify
sudo ldconfig

# Install libewf 
cd /tmp
git clone https://github.com/libyal/libewf
cd libewf
./synclibs.sh
./autogen.sh
./configure --enable-v1-api --enable-python
make
sudo make install
sudo ldconfig
#sudo wget https://53efc0a7187d0baa489ee347026b8278fe4020f6.googledrive.com/host/0B3fBvzttpiiSMTdoaVExWWNsRjg/libewf-20140608.tar.gz
#tar -xzvf libewf-20140608.tar.gz
#cd libewf-20140608
#bootstrap
#./configure --enable-v1-api
#make
#sudo make install
#sudo ldconfig

# Install libqcow (needed for current pytsk)
cd /tmp
wget https://github.com/libyal/libqcow/releases/download/20150105/libqcow-alpha-20150105.tar.gz
tar zxvf libqcow-alpha-20150105.tar.gz
cd libqcow-20150105
./configure --enable-python
make
sudo make install
sudo ldconfig

# Install sleuthkit
cd /tmp
wget https://github.com/sleuthkit/sleuthkit/archive/sleuthkit-4.2.0.tar.gz -O sleuthkit-4.2.0.tar.gz
tar zxvf sleuthkit-4.2.0.tar.gz
cd sleuthkit-sleuthkit-4.2.0
./bootstrap
make
sudo make install
sudo ldconfig
#sudo wget http://sourceforge.net/projects/sleuthkit/files/latest/download?source=files -O sleuthkit.tar.gz
#tar -xzvf sleuthkit.tar.gz
#wget https://4a014e8976bcea5c2cd7bfa3cac120c3dd10a2f1.googledrive.com/host/0B3fBvzttpiiScUxsUm54cG02RDA/tsk4.1.3_external_type.patch
#sed  -i '/TSK_IMG_TYPE_EWF_EWF = 0x0040,  \/\/\/< EWF version/a \
#\
#        TSK_IMG_TYPE_EXTERNAL = 0x1000,  \/\/\/< external defined format which at least implements TSK_IMG_INFO, used by pytsk' /tmp/sleuthkit-4.1.3/tsk/img/tsk_img.h
#cd sleuthkit-4.1.3
#./configure
#make
#sudo make install
#sudo ldconfig

# Python TSK bindings
cd /tmp
git clone https://github.com/py4n6/pytsk
cd pytsk
python setup.py build
sudo python setup.py install

# Install scipy
sudo pip install scipy
sudo pip install numpy
sudo pip install pandas
sudo pip install redis
sudo pip install tornado
sudo pip install greenlet
sudo pip install pyzmq
# Already have dateutil - kept here for reference
#sudo pip install python-dateutil

# Bokeh testing dependencies
sudo pip install beautifulsoup
sudo pip install colorama
# Couldn't find pdiff???
#sudo pip install pdiff
sudo pip install boto
sudo pip install nose
sudo pip install mock
sudo pip install coverage
sudo pip install websocket-client

# Install blaze for future stuff
sudo pip install blaze

# Now install some additional deps and bokeh itself (npm and node)
sudo apt-get install -y npm node
sudo pip install bokeh

# FOR REFERENCE ONLY - download bokeh samples
#>>> import bokeh.sampledata
#>>> bokeh.sampledata.download()

# Now install Bokeh from source
##cd /tmp
##git clone https://github.com/bokeh/bokeh.git
##cd bokeh/bokehjs
# More instruction here if we decide to do this in the future. For now, pip.

# link to the shared image folder
#sudo mkdir /home/bcadmin
#sudo ln -s /vagrant/disk-images /home/bcadmin/disk_images

#start the server
#cd /vagrant
#python runserver.py &
