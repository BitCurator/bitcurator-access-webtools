#!/usr/bin/env bash
#
# bootstrap.sh: Build and configuration script for bitcurator-access-webtools in Vagrant
# --------------------------------------------------------------------------------------
# Build and populate the VM: install and/or compile the necessary
# tools needed to run the bitcurator-access-webtools Flask application.
#
# This script is only the *first time* you issue the command:
#
#    vagrant up
#
# Or, following the commands:
#
#    (vagrant halt)
#    vagrant destroy
#    vagrant up
#
# See the README.md for further detais.
#
#===============================================================================
# vim: softtabstop=4 shiftwidth=4 expandtab fenc=utf-8 spell spelllang=en cc=81
#===============================================================================
#
# Script Version
__ScriptVersion="0.7"
# Base directory for build log
LOG_BASE=/var/log
WWW_ROOT=/var/www
BCAW_ROOT="$WWW_ROOT/bcaw"
BCAW_TARGET="$BCAW_ROOT/bcaw"
DISK_IMAGE_TARGET="$BCAW_ROOT/disk-images"
SOURCE_ROOT="/vagrant"
BCAW_SOURCE="$SOURCE_ROOT/bcaw"
DISK_IMAGE_SOURCE="$SOURCE_ROOT/disk-images"
#--- FUNCTION ----------------------------------------------------------------
# NAME: __function_defined
# DESCRIPTION: Checks if a function is defined within this scripts scope
# PARAMETERS: function name
# RETURNS: 0 or 1 as in defined or not defined
#-------------------------------------------------------------------------------
__function_defined() {
    FUNC_NAME=$1
    if [ "$(command -v $FUNC_NAME)x" != "x" ]; then
        echoinfo "Found function $FUNC_NAME"
        return 0
    fi

    echodebug "$FUNC_NAME not found...."
    return 1
}

#--- FUNCTION ----------------------------------------------------------------
# NAME: __strip_duplicates
# DESCRIPTION: Strip duplicate strings
#-------------------------------------------------------------------------------
__strip_duplicates() {
    echo "$@" | tr -s '[:space:]' '\n' | awk '!x[$0]++'
}

#--- FUNCTION ----------------------------------------------------------------
# NAME: echoerr
# DESCRIPTION: Echo errors to stderr.
#-------------------------------------------------------------------------------
echoerror() {
    printf "%s * ERROR%s: %s\n" "${RC}" "${EC}" "$@" 1>&2;
}

#--- FUNCTION ----------------------------------------------------------------
# NAME: echoinfo
# DESCRIPTION: Echo information to stdout.
#-------------------------------------------------------------------------------
echoinfo() {
    printf "%s * STATUS%s: %s\n" "${GC}" "${EC}" "$@";
}

#--- FUNCTION ----------------------------------------------------------------
# NAME: echowarn
# DESCRIPTION: Echo warning informations to stdout.
#-------------------------------------------------------------------------------
echowarn() {
    printf "%s * WARN%s: %s\n" "${YC}" "${EC}" "$@";
}

#--- FUNCTION ----------------------------------------------------------------
# NAME: echodebug
# DESCRIPTION: Echo debug information to stdout.
#-------------------------------------------------------------------------------
echodebug() {
    if [ $_ECHO_DEBUG -eq $BS_TRUE ]; then
        printf "${BC} * DEBUG${EC}: %s\n" "$@";
    fi
}
#---  FUNCTION  ----------------------------------------------------------------
#          NAME:  __apt_get_install_noinput
#   DESCRIPTION:  (DRY) apt-get install with noinput options
#-------------------------------------------------------------------------------
__apt_get_install_noinput() {
    apt-get install -y -o DPkg::Options::=--force-confold "$@"; return $?
}

#---  FUNCTION  ----------------------------------------------------------------
#          NAME:  __apt_get_upgrade_noinput
#   DESCRIPTION:  (DRY) apt-get upgrade with noinput options
#-------------------------------------------------------------------------------
__apt_get_upgrade_noinput() {
    apt-get upgrade -y -o DPkg::Options::=--force-confold; return $?
}

#---  FUNCTION  ----------------------------------------------------------------
#          NAME:  __pip_install_noinput
#   DESCRIPTION:  (DRY)
#-------------------------------------------------------------------------------
__pip_install_noinput() {
    pip install --upgrade "$@"; return $?
    # Uncomment for Python 3
    #pip3 install --upgrade $@; return $?
}

#---  FUNCTION  ----------------------------------------------------------------
#          NAME:  __pip_install_noinput
#   DESCRIPTION:  (DRY)
#-------------------------------------------------------------------------------
__pip_pre_install_noinput() {
    pip install --pre --upgrade "$@"; return $?
    # Uncomment for Python 3
    # pip3 install --pre --upgrade $@; return $?
}


#---  FUNCTION  ----------------------------------------------------------------
#          NAME:  __check_apt_lock
#   DESCRIPTION:  (DRY)
#-------------------------------------------------------------------------------
__check_apt_lock() {
    lsof /var/lib/dpkg/lock > /dev/null 2>&1
    RES=`echo $?`
    return $RES
}

__enable_universe_repository() {
    if [ "x$(grep -R universe /etc/apt/sources.list /etc/apt/sources.list.d/ | grep -v '#')" != "x" ]; then
        # The universe repository is already enabled
        return 0
    fi

    echodebug "Enabling the universe repository"

    # Ubuntu versions higher than 12.04 do not live in the old repositories
    if [ $DISTRO_MAJOR_VERSION -gt 12 ] || ([ $DISTRO_MAJOR_VERSION -eq 12 ] && [ $DISTRO_MINOR_VERSION -gt 04 ]); then
        add-apt-repository -y "deb http://archive.ubuntu.com/ubuntu $(lsb_release -sc) universe" || return 1
    elif [ $DISTRO_MAJOR_VERSION -lt 11 ] && [ $DISTRO_MINOR_VERSION -lt 10 ]; then
        # Below Ubuntu 11.10, the -y flag to add-apt-repository is not supported
        add-apt-repository "deb http://old-releases.ubuntu.com/ubuntu $(lsb_release -sc) universe" || return 1
    fi

    add-apt-repository -y "deb http://old-releases.ubuntu.com/ubuntu $(lsb_release -sc) universe" || return 1

    return 0
}

__check_unparsed_options() {
    shellopts="$1"
    # grep alternative for SunOS
    if [ -f /usr/xpg4/bin/grep ]; then
        grep='/usr/xpg4/bin/grep'
    else
        grep='grep'
    fi
    unparsed_options=$( echo "$shellopts" | ${grep} -E '(^|[[:space:]])[-]+[[:alnum:]]' )
    if [ "x$unparsed_options" != "x" ]; then
        usage
        echo
        echoerror "options are only allowed before install arguments"
        echo
        exit 1
    fi
}

configure_cpan() {
    (echo y;echo o conf prerequisites_policy follow;echo o conf commit)|cpan > /dev/null
}

usage() {
    echo "usage"
    exit 1
}

install_ubuntu_14.04_deps() {

    echoinfo "Updating your APT Repositories ... "
    apt-get update >> $LOG_BASE/bca-install.log 2>&1 || return 1

    echoinfo "Installing Python Software Properies ... "
    __apt_get_install_noinput software-properties-common >> $LOG_BASE/bca-install.log 2>&1  || return 1

    echoinfo "Enabling Universal Repository ... "
    __enable_universe_repository >> $LOG_BASE/bca-install.log 2>&1 || return 1

    echoinfo "Enabling openjdk-r PPA for OpenJDK 8 in 14.04LTS ... "
    add-apt-repository -y ppa:openjdk-r/ppa >> $LOG_BASE/bca-install.log 2>&1 || return 1

    echoinfo "Enabling mc3man PPA for ffmpeg ... "
    add-apt-repository -y ppa:mc3man/trusty-media >> $LOG_BASE/bca-install.log 2>&1 || return 1

    echoinfo "Updating Repository Package List ..."
    apt-get update >> $LOG_BASE/bca-install.log 2>&1 || return 1

    echoinfo "Upgrading all packages to latest version ..."
    __apt_get_upgrade_noinput >> $LOG_BASE/bca-install.log 2>&1 || return 1

    return 0
}

install_ubuntu_16.04_deps() {

    echoinfo "Updating your APT Repositories ... "
    apt-get update >> $LOG_BASE/bca-install.log 2>&1 || return 1

    echoinfo "Installing Python Software Properies ... "
    __apt_get_install_noinput software-properties-common >> $LOG_BASE/bca-install.log 2>&1  || return 1

    echoinfo "Enabling Universal Repository ... "
    __enable_universe_repository >> $LOG_BASE/bca-install.log 2>&1 || return 1

    # TESTING ONLY - DO NOT UNCOMMENT
    # echoinfo "Adding Oracle Java Repository"
    # add-apt-repository -y ppa:webupd8team/java >> $LOG_BASE/bca-install.log 2>&1 || return 1
    # Need oracle-java8-installer to replace openjdk in package list below (future)

    echoinfo "Updating Repository Package List ..."
    apt-get update >> $LOG_BASE/bca-install.log 2>&1 || return 1

    echoinfo "Upgrading all packages to latest version ..."
    __apt_get_upgrade_noinput >> $LOG_BASE/bca-install.log 2>&1 || return 1

    return 0
}

#
# Packages below will be installed. Dependencies listed here:
# Various: subversion, libatlass-base-dev, gcc, gfortran, g++, build-essential, libtool, autmoate
# Access Git repositories: git
# libewf specific depends: bison, flex, zlib1g-dev, libtalloc2, libtalloc-dev
# pyewf specific depends: python, python-dev, python-pip
# Postgres: postgresql, pgadmin3, postgresql-server-dev-9.3
# Text extraction: antiword, poppler-utils
# Java: openjdk-7-*, ant-*, ivy-*
#  openjdk-7-jdk
#  openjdk-7-jre-headless
#  openjdk-7-jre-lib
# Bokeh: npm, node
# textract: python-dev libxml2-dev libxslt1-dev antiword unrtf poppler-utils pstotext tesseract-ocr flac ffmpeg lame libmad0 libsox-fmt-mp3 sox libjpeg-dev zlib1g-dev

install_ubuntu_14.04_packages() {
    packages="dkms
ant
ant-doc
ant-optional
antiword
automake
autopoint
bison
build-essential
ffmpeg
flac
flex
g++
gcc
gfortran
git
ivy
ivy-doc
python
python-pip
python-dev
python-virtualenv
nginx
zlib1g-dev
lame
libatlas-base-dev
libjpeg-dev
libmad0
libtalloc2
libtalloc-dev
libtool
libpcre3
libpcre3-dev
libsox-fmt-mp3
libxml2-dev
libxslt1-dev
odt2txt
openjdk-8-jdk
openjdk-8-jre-headless
poppler-utils
postgresql
pgadmin3
postgresql-server-dev-9.3
pstotext
rabbitmq-server
redis-server
sox
subversion
tesseract-ocr
unrtf
uwsgi
uwsgi-plugin-python
zlib1g-dev"

    if [ "$@" = "dev" ]; then
        packages="$packages"
    elif [ "$@" = "stable" ]; then
        packages="$packages"
    fi

    for PACKAGE in $packages; do
        __apt_get_install_noinput $PACKAGE >> $LOG_BASE/bca-install.log 2>&1
        ERROR=$?
        if [ $ERROR -ne 0 ]; then
            echoerror "Install Failure: $PACKAGE (Error Code: $ERROR)"
        else
            echoinfo "Installed Package: $PACKAGE"
        fi
    done

    return 0
}

#
# Packages below will be installed. Dependencies listed here:
# Various: subversion, libatlass-base-dev, gcc, gfortran, g++, build-essential, libtool, autmoate
# Access Git repositories: git
# libewf specific depends: bison, flex, zlib1g-dev, libtalloc2, libtalloc-dev
# pyewf specific depends: python, python-dev, python-pip
# Postgres: postgresql, pgadmin3, postgresql-server-dev-9.3
# Text extraction: antiword, poppler-utils
# Java: openjdk-7-*, ant-*, ivy-*
# Bokeh: npm, node
# Celery: celeryd (don't use, deprecated)

install_ubuntu_16.04_packages() {
    packages="dkms
ant
ant-doc
ant-optional
antiword
automake
autopoint
bison
build-essential
ffmpeg
flac
flex
g++
gcc
gfortran
git
ivy
ivy-doc
jcc
python
python-pip
python-dev
python-virtualenv
nginx
zlib1g-dev
lame
libatlas-base-dev
libjpeg-dev
libmad0
libtalloc2
libtalloc-dev
libtool
libpcre3
libpcre3-dev
libsox-fmt-mp3
libxml2-dev
libxslt1-dev
odt2txt
openjdk-8-jdk
openjdk-8-jre-headless
poppler-utils
postgresql
pgadmin3
postgresql-server-dev-9.5
pstotext
rabbitmq-server
redis-server
sox
subversion
tesseract-ocr
unrtf
uwsgi
uwsgi-plugin-python
zlib1g-dev"

    if [ "$@" = "dev" ]; then
        packages="$packages"
    elif [ "$@" = "stable" ]; then
        packages="$packages"
    fi

    for PACKAGE in $packages; do
        __apt_get_install_noinput $PACKAGE >> $LOG_BASE/bca-install.log 2>&1
        ERROR=$?
        if [ $ERROR -ne 0 ]; then
            echoerror "Install Failure: $PACKAGE (Error Code: $ERROR)"
        else
            echoinfo "Installed Package: $PACKAGE"
        fi
    done

    return 0
}

install_ubuntu_14.04_pip_packages() {

#
# Packages below will be installed. Dependencies listed here:
# Flask and postgres support: psycopg2, Flask-SQLAlchemy, flask-wtf
# Scipy: scipy, numpy, pandas, redis, tornado, greenlet, pyzmq
# Bokeh: beautifulsoup, colorama, boto, nose, mock, coverage, websocket-client, blaze, bokeh
# Celery: celery
#

pip_packages="flask
psycopg2
Flask-SQLAlchemy
flask-wtf
celery
nltk
numpy
textract"

    pip_pre_packages="bitstring"

    if [ "$@" = "dev" ]; then
        pip_packages="$pip_packages"
    elif [ "$@" = "stable" ]; then
        pip_packages="$pip_packages"
    fi

    ERROR=0
    for PACKAGE in $pip_pre_packages; do
        CURRENT_ERROR=0
        echoinfo "Installed Python (pre) Package: $PACKAGE"
        __pip_pre_install_noinput $PACKAGE >> $LOG_BASE/bca-install.log 2>&1 || (let ERROR=ERROR+1 && let CURRENT_ERROR=1)
        if [ $CURRENT_ERROR -eq 1 ]; then
            echoerror "Python Package Install Failure: $PACKAGE"
        fi
    done

    for PACKAGE in $pip_packages; do
        CURRENT_ERROR=0
        echoinfo "Installed Python Package: $PACKAGE"
        __pip_install_noinput $PACKAGE >> $LOG_BASE/bca-install.log 2>&1 || (let ERROR=ERROR+1 && let CURRENT_ERROR=1)
        if [ $CURRENT_ERROR -eq 1 ]; then
            echoerror "Python Package Install Failure: $PACKAGE"
        fi
    done

    if [ $ERROR -ne 0 ]; then
        echoerror
        return 1
    fi

    return 0
}

install_ubuntu_16.04_pip_packages() {

#
# Packages below will be installed. Dependencies listed here:
# Flask and postgres support: psycopg2, Flask-SQLAlchemy, flask-wtf
# Scipy: scipy, numpy, pandas, redis, tornado, greenlet, pyzmq
# Bokeh: beautifulsoup, colorama, boto, nose, mock, coverage, websocket-client, blaze, bokeh
# Celery: celery
#

pip_packages="flask
psycopg2
Flask-SQLAlchemy
flask-wtf
celery
nltk
numpy"

    source "$BCAW_ROOT/venv/bin/activate"

    pip_pre_packages="bitstring"

    if [ "$@" = "dev" ]; then
        pip_packages="$pip_packages"
    elif [ "$@" = "stable" ]; then
        pip_packages="$pip_packages"
    fi

    ERROR=0
    for PACKAGE in $pip_pre_packages; do
        CURRENT_ERROR=0
        echoinfo "Installed Python (pre) Package: $PACKAGE"
        __pip_pre_install_noinput $PACKAGE >> $LOG_BASE/bca-install.log 2>&1 || (let ERROR=ERROR+1 && let CURRENT_ERROR=1)
        if [ $CURRENT_ERROR -eq 1 ]; then
            echoerror "Python Package Install Failure: $PACKAGE"
        fi
    done

    for PACKAGE in $pip_packages; do
        CURRENT_ERROR=0
        echoinfo "Installed Python Package: $PACKAGE"
        __pip_install_noinput $PACKAGE >> $LOG_BASE/bca-install.log 2>&1 || (let ERROR=ERROR+1 && let CURRENT_ERROR=1)
        if [ $CURRENT_ERROR -eq 1 ]; then
            echoerror "Python Package Install Failure: $PACKAGE"
        fi
    done

    if [ $ERROR -ne 0 ]; then
        echoerror
        return 1
    fi

    return 0
}


install_source_packages() {

  source "$BCAW_ROOT/venv/bin/activate"

  # Install pylucene (also installs JCC)
  echoinfo "bitcurator-access-webtools: Building and installing pylucene"
  echoinfo " -- This may take several minutes..."
        cd /tmp
        wget http://apache.claz.org/lucene/pylucene/pylucene-6.2.0-src.tar.gz >> $LOG_BASE/bca-install.log 2>&1
        tar -zxvf pylucene-6.2.0-src.tar.gz >> $LOG_BASE/bca-install.log 2>&1
        cd pylucene-6.2.0
        export JAVA_HOME=/usr/lib/jvm/java-8-openjdk-amd64
        export JCC_JDK=/usr/lib/jvm/java-8-openjdk-amd64

        pushd jcc >> $LOG_BASE/bca-install.log 2>&1

        # Must manually tweak setup.py for JCC with openjdk8 - JCC build will fail
        # without this!
        sed -i "s/java-8-oracle/java-8-openjdk-amd64/g" setup.py

        python setup.py build >> $LOG_BASE/bca-install.log 2>&1
        python setup.py install >> $LOG_BASE/bca-install.log 2>&1
        popd >> $LOG_BASE/bca-install.log 2>&1

        # Edit the Makefile to uncomment the config info for Linux.
        # First we look for the requred string in the makefile and copy the 5 lines
        # strting from the 4th line after the pattern match, into a temp file (temp),
        # after removing the leading hash (to uncomment the lines).

        # Then we fix some paths for the virtualenv.

        # Then we append these lines from temp file to Makefile after the given pattern
        # is found.
        grep -A 8 "Debian Jessie 64-bit" Makefile | sed -n '4,8p' | sed 's/^#//' > temp
        #sed -i "s/PREFIX_PYTHON=\/usr/PREFIX_PYTHON=\/var\/www\/bcaw\/venv/g" temp
        sed -i "s/PREFIX_PYTHON=\/opt\/apache\/pylucene\/_install/PREFIX_PYTHON=\/var\/www\/bcaw\/venv/g" temp
        sed -i "s/ANT=JAVA_HOME=\/usr\/lib\/jvm\/java-8-oracle/ANT=JAVA_HOME=\/usr\/lib\/jvm\/java-8-openjdk-amd64/g" temp
        sed -i -e '/Debian Jessie 64-bit/r temp' Makefile

        # Finally, remove the shared flag for the time being. See
        # http://lucene.apache.org/pylucene/jcc/install.html for why the shared
        # flag is used. Setuptools in 14.04LTS is not properly patched for this right now.
        sed -i "s/JCC=\$(PYTHON)\ -m\ jcc\ --shared/JCC=\$(PYTHON)\ -m\ jcc/g" Makefile

        make >> $LOG_BASE/bca-install.log 2>&1
        sudo make install |& sudo tee -a $LOG_BASE/bca-install.log
        sudo ldconfig
        # Clean up
        # rm -rf /tmp/pylucene-6.2.0*

        #wget http://apache.mirrors.pair.com/lucene/pylucene/pylucene-4.10.1-1-src.tar.gz >> $LOG_BASE/bca-install.log 2>&1
        #tar -zxvf pylucene-4.10.1-1-src.tar.gz >> $LOG_BASE/bca-install.log 2>&1
        #cd pylucene-4.10.1-1
        #pushd jcc >> $LOG_BASE/bca-install.log 2>&1
        #python setup.py build >> $LOG_BASE/bca-install.log 2>&1
        #python setup.py install >> $LOG_BASE/bca-install.log 2>&1
        #popd >> $LOG_BASE/bca-install.log 2>&1

        # Edit the Makefile to uncomment the config info for Linux.
        # First we look for the requred string in the makefile and copy the 5 lines
        # strting from the 4th line after the pattern match, into a temp file (temp),
        # after removing the leading hash (to uncomment the lines).

        # Then we fix some paths for the virtualenv.

        # Then we append these lines from temp file to Makefile after the given pattern
        # is found.
        #grep -A 8 "Ubuntu 11.10 64-bit" Makefile | sed -n '4,8p' | sed 's/^#//' > temp
        #sed -i "s/PREFIX_PYTHON=\/usr/PREFIX_PYTHON=\/var\/www\/bcaw\/venv/g" temp
        #sed -i -e '/Ubuntu 11.10 64-bit/r temp' Makefile
        #make >> $LOG_BASE/bca-install.log 2>&1
        #sudo make install >> $LOG_BASE/bca-install.log 2>&1
        #sudo ldconfig
        ## Clean up
        #rm -rf /tmp/pylucene-4.10.1.-1*

  # Checking postgres setup
  echoinfo "bitcurator-access-webtools: Checking postgres setup"
        cd /tmp
        check_install postgresql postgresql >> $LOG_BASE/bca-install.log 2>&1

  # Starting postgres
  echoinfo "bitcurator-access-webtools: Starting postgres service and creating DB"
        # Commented out - not needed currently???
        # .pgpass contains the password for the vagrant user. Needs to be in the home directory.
        #sudo cp /vagrant/.pgpass /home/vagrant/.pgpass

        # Start postgress and setup up postgress user
        sudo service postgresql start

        # Create the database bca_db with owner vagrant
        # Create user first
  echoinfo "bitcurator-access-webtools: Creating postgres user"
        sudo -u postgres psql -c"CREATE user vagrant WITH PASSWORD 'vagrant'"

        # Create the database
  echoinfo "bitcurator-access-webtools: Creating bca_db database"
        sudo -u postgres createdb -O vagrant bca_db

        # Legacy - kept for reference
        #sudo -u postgres psql -c"ALTER user postgres WITH PASSWORD 'bcadmin'"
        #sudo -u postgres psql -c"CREATE user bcadmin WITH PASSWORD 'bcadmin'"
        #sudo -u postgres createdb -O bcadmin bcdb

        # Restart postgres
        sudo service postgresql restart

        # Verify
        sudo ldconfig

        # Install libuna from dedicated copy
        echoinfo "bitcurator-access-webtools: Building and installing libuna..."
        cd /tmp
        cp /vagrant/externals/libuna-alpha-20150927.tar.gz .
        tar zxvf libuna-alpha-20150927.tar.gz >> $LOG_BASE/bca-install.log 2>&1
        cd libuna-20150927
        ./configure >> $LOG_BASE/bca-install.log 2>&1
        make -s >> $LOG_BASE/bca-install.log 2>&1
        make install >> $LOG_BASE/bca-install.log 2>&1
        ldconfig >> $LOG_BASE/bca-install.log 2>&1

        # Now clean up
        rm -rf /tmp/libuna-20150927


        # Install libewf from dedicated copy
        echoinfo "bitcurator-access-webtools: Building and installing libewf..."
        cd /tmp
        cp /vagrant/externals/libewf-20140608.tar.gz .
        tar zxvf libewf-20140608.tar.gz >> $LOG_BASE/bca-install.log 2>&1
        cd libewf-20140608
        ./configure --enable-python --enable-v1-api >> $LOG_BASE/bca-install.log 2>&1
        make -s >> $LOG_BASE/bca-install.log 2>&1
        make install >> $LOG_BASE/bca-install.log 2>&1
        ldconfig >> $LOG_BASE/bca-install.log 2>&1

        # Now clean up
        rm -rf /tmp/libewf-20140608


  # Install libqcow (needed for pytsk)
  echoinfo "bitcurator-access-webtools: Building and installing libqcow..."
        cd /tmp
        wget -q https://github.com/libyal/libqcow/releases/download/20160123/libqcow-alpha-20160123.tar.gz >> $LOG_BASE/bca-install.log 2>&1
        tar zxvf libqcow-alpha-20160123.tar.gz >> $LOG_BASE/bca-install.log 2>&1
        cd libqcow-20160123
        ./configure --enable-python >> $LOG_BASE/bca-install.log 2>&1
        make >> $LOG_BASE/bca-install.log 2>&1
        sudo make install |& sudo tee -a  $LOG_BASE/bca-install.log
        sudo ldconfig

  # Install The Sleuth Kit
  echoinfo "bitcurator-access-webtools: Building and installing The Sleuth Kit..."
        cd /tmp
        wget https://github.com/sleuthkit/sleuthkit/archive/sleuthkit-4.2.0.tar.gz -O sleuthkit-4.2.0.tar.gz >> $LOG_BASE/bca-install.log 2>&1
        tar zxvf sleuthkit-4.2.0.tar.gz >> $LOG_BASE/bca-install.log 2>&1
        cd sleuthkit-sleuthkit-4.2.0
        ./bootstrap >> $LOG_BASE/bca-install.log 2>&1
        ./configure >> $LOG_BASE/bca-install.log 2>&1
        make >> $LOG_BASE/bca-install.log 2>&1
        sudo make install |& sudo tee -a $LOG_BASE/bca-install.log
        sudo ldconfig
        # Clean up
        rm /tmp/sleuthkit-4.2.0.tar.gz
        rm -rf /tmp/sleuthkit-sleuthkit-4.2.0

  # Install TSK Python bindings
  echoinfo "bitcurator-access-webtools: Building and installing pytsk..."
        cd /tmp
        #git clone https://github.com/py4n6/pytsk >> $LOG_BASE/bca-install.log 2>&1
        wget -q https://github.com/py4n6/pytsk/releases/download/20150406/pytsk-20150406.tgz
        tar zxvf pytsk-20150406.tgz >> $LOG_BASE/bca-install.log 2>&1
        cd pytsk
        #python setup.py build >> $LOG_BASE/bca-install.log 2>&1
        "$BCAW_ROOT/venv/bin/python" setup.py build >> $LOG_BASE/bca-install.log 2>&1
        #python setup.py build >> $LOG_BASE/bca-install.log 2>&1
        #sudo python setup.py install >> $LOG_BASE/bca-install.log 2>&1
        # Modified for use in virtualenv
        "$BCAW_ROOT/venv/bin/python" setup.py install >> $LOG_BASE/bca-install.log 2>&1
        # Clean up
        rm -rf /tmp/pytsk
}

create_virtualenv() {
  echoinfo "bitcurator-access-webtools: Creating and activating Python virtualenv..."
  if [ -d "$WWW_ROOT" ]; then
  	rm -rf "$WWW_ROOT"
  fi
   mkdir "$WWW_ROOT"
   mkdir "$BCAW_ROOT"
   chmod -R 777 "$BCAW_ROOT"
   chown -R www-data:www-data "$BCAW_ROOT"
   virtualenv "$BCAW_ROOT/venv"
   source "$BCAW_ROOT/venv/bin/activate"
}

copy_source() {
  echoinfo "bitcurator-access-webtools: Copying BCA Webtools source..."
  if [ -d "$BCAW_TARGET" ]; then
    rm "$BCAW_ROOT/"*.pyc
    find "$BCAW_TARGET" -name "*.pyc" -type f -exec rm {} \;
  fi

  cp -f "$SOURCE_ROOT/"*.py "$BCAW_ROOT"
  cp -fr "$BCAW_SOURCE" "$BCAW_ROOT"
  chown www-data:www-data "$BCAW_ROOT/"*.py
  chown -R www-data:www-data "$BCAW_TARGET"
}

copy_disk_images() {
  echoinfo "bitcurator-access-webtools: Copying disk images from source..."
   cp -r "$DISK_IMAGE_SOURCE" "$BCAW_ROOT"
   chown -R www-data:www-data "$DISK_IMAGE_TARGET"
   chmod 777 "$DISK_IMAGE_TARGET"
   chmod 666 "$DISK_IMAGE_TARGET/"*
}

configure_webstack() {
  echoinfo "bitcurator-access-webtools: Configuring BCA Webtools web stack..."

   # Temporary: Create and perm-fix log file
  echoinfo "bitcurator-access-webtools: Preparing log file"
  sudo touch /var/log/bcaw.log
  sudo chmod 666 /var/log/bcaw.log

  if [ -d "$WWW_ROOT/run" ]; then
    rm -rf "$WWW_ROOT/run"
  fi

   mkdir "$WWW_ROOT/run"
   chown www-data:www-data "$WWW_ROOT/run"
   chmod 777 "$WWW_ROOT/run"

   touch /var/log/uwsgi/emperor.log
   chown www-data:www-data /var/log/uwsgi/emperor.log
   chmod 666 /var/log/uwsgi/emperor.log

   touch /var/log/uwsgi/app/bcaw.log
   chown www-data:www-data /var/log/uwsgi/app/bcaw.log
   chmod 666 /var/log/uwsgi/app/bcaw.log

   cp /vagrant/uwsgi.conf /etc/init
   cp /vagrant/uwsgi_config.ini /etc/uwsgi/apps-available/
   ln -s /etc/uwsgi/apps-available/uwsgi_config.ini /etc/uwsgi/apps-enabled

   # NGINX Setup
   rm /etc/nginx/sites-enabled/default
   cp /vagrant/nginx_config /etc/nginx/sites-available/
   ln -s /etc/nginx/sites-available/nginx_config /etc/nginx/sites-enabled

   # Start UWSGI and NGINX
   echoinfo "bitcurator=access-webtools: Restarting nginx.....";
   service nginx restart
   # Future: use systemctl for 16.04
   #systemctl restart nginx
   echoinfo "bitcurator-access-webtools: starting usgi.....";
   service uwsgi start
   # Future: use systemctl for 16.04
   #systemctl start uwsgi

   # Give vagrant user access to www-data
   usermod -a -G www-data vagrant

}

complete_message() {
    echo
    echo "Installation Complete!"
    echo
    echo "Additional documentation at: http://access.bitcurator.net"
    echo
}

#UPGRADE_ONLY=0
#CONFIGURE_ONLY=0
#SKIN=0
#INSTALL=0
#YESTOALL=0

OS=$(lsb_release -si)
ARCH=$(uname -m | sed 's/x86_//;s/i[3-6]86/32/')
VER=$(lsb_release -sr)

if [ $OS != "Ubuntu" ]; then
    echo "bitcurator-access-webtools is only installable on Ubuntu operating systems at this time."
    exit 1
fi

#if [ $ARCH != "64" ]; then
#    echo "bitcurator-access-webtools is only installable on a 64-bit architecture at this time."
#    exit 2
#fi

if [ $VER != "14.04" ] && [ $VER != "16.04" ]; then
    echo "bitcurator-access-webtools is only installable on Ubuntu 14.04 and 16.04 at this time."
    exit 3
fi

if [ "`whoami`" != "root" ]; then
    echoerror "The bitcurator-access-webtools bootstrap script must run as root."
    echoinfo "Preferred Usage: sudo bootstrap.sh (options)"
    echo ""
    exit 3
fi

if [ "$SUDO_USER" = "" ]; then
    echo "The SUDO_USER variable doesn't seem to be set"
    exit 4
fi

#    echo "APT Package Manager appears to be locked. Close all package managers."
#    exit 15
#fi

# while getopts ":hvcsiyu" opt
while getopts ":hv" opt
do
case "${opt}" in
    h ) usage; exit 0 ;;
    v ) echo "$0 -- Version $__ScriptVersion"; exit 0 ;;
    \?) echo
        echoerror "Option does not exist: $OPTARG"
        usage
        exit 1
        ;;
esac
done

shift $(($OPTIND-1))

if [ "$#" -eq 0 ]; then
    ITYPE="stable"
else
    __check_unparsed_options "$*"
    ITYPE=$1
    shift
fi

# Check installation type
if [ "$(echo $ITYPE | egrep '(dev|stable)')x" = "x" ]; then
    echoerror "Installation type \"$ITYPE\" is not known..."
    exit 1
fi

echoinfo "*********************************************************************"
echoinfo "The bitcurator-access-webtools script will now configure your system."
echoinfo "*********************************************************************"
echoinfo ""

#if [ "$YESTOALL" -eq 1 ]; then
#    echoinfo "You supplied the -y option, this script will not exit for any reason"
#fi

echoinfo "OS: $OS"
echoinfo "Arch: $ARCH"
echoinfo "Version: $VER"
echoinfo "The current user is: $SUDO_USER"

#if [ "$SKIN" -eq 1 ] && [ "$YESTOALL" -eq 0 ]; then
#    echo
#    echo "You have chosen to apply the BitCurator skin to the Ubuntu system."
#    echo
#    echo "You did not choose to say YES to all, so we are going to exit."
#    echo
#    echo
#    echo "Re-run this command with the -y option"
#    echo
#    exit 10
#fi

#if [ "$INSTALL" -eq 1 ] && [ "$CONFIGURE_ONLY" -eq 0 ]; then

    export DEBIAN_FRONTEND=noninteractive
    install_ubuntu_${VER}_deps $ITYPE
    install_ubuntu_${VER}_packages $ITYPE
    create_virtualenv
    install_ubuntu_${VER}_pip_packages $ITYPE
    install_source_packages
    copy_disk_images

    copy_source
    configure_webstack

#fi

#configure_elasticsearch

# Configure for BitCurator
# configure_ubuntu

# Configure BitCurator VM (if selected)
#if [ "$SKIN" -eq 1 ]; then
#    configure_ubuntu_bitcurator_vm
#    configure_ubuntu_${VER}_bitcurator_vm
#fi

complete_message

#if [ "$SKIN" -eq 1 ]; then
#    complete_message_skin
#fi

# REFERENCE ONLY - DO NOT UNCOMMENT

  # link to the shared image folder
  #sudo mkdir /home/bcadmin
  #sudo ln -s /vagrant/disk-images /home/bcadmin/disk_images
