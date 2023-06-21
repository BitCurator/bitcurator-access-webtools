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
__ScriptVersion="0.7.1"
# Base directory for build log
LOG_BASE=/var/log
WWW_ROOT=/var/www
BCAW_ROOT="$WWW_ROOT/bcaw"
BCAW_TARGET="$BCAW_ROOT/bcaw"
DISK_IMAGE_TARGET="$BCAW_ROOT/disk-images"
CONF_TARGET="$BCAW_ROOT/conf"
SOURCE_ROOT="/vagrant"
BCAW_SOURCE="$SOURCE_ROOT/bcaw"
DISK_IMAGE_SOURCE="$SOURCE_ROOT/disk-images"
CONF_SOURCE="$SOURCE_ROOT/conf"
LUCENE_INDEX="$WWW_ROOT/.index"
CACHE_DIR="$WWW_ROOT/.cache"
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

install_ubuntu_deps() {

    echoinfo "Updating your APT Repositories ... "
    apt-get update >> $LOG_BASE/bca-install.log 2>&1 || return 1

    echoinfo "Installing Python Software Properies ... "
    __apt_get_install_noinput software-properties-common >> $LOG_BASE/bca-install.log 2>&1  || return 1

    echoinfo "Enabling Universal Repository ... "
    __enable_universe_repository >> $LOG_BASE/bca-install.log 2>&1 || return 1

    # Reference only - use OpenJDK in current build
    # echoinfo "Adding Oracle Java Repository"
    # add-apt-repository -y ppa:webupd8team/java >> $LOG_BASE/bca-install.log 2>&1 || return 1

    echoinfo "Updating Repository Package List ..."
    apt-get update >> $LOG_BASE/bca-install.log 2>&1 || return 1

    echoinfo "Upgrading all packages to latest version ..."
    __apt_get_upgrade_noinput >> $LOG_BASE/bca-install.log 2>&1 || return 1

    return 0
}

#
# Packages below will be installed.
# Packages are listed in alphabetic order for convenience.
#
# Dependencies listed here:
# Core: subversion, libatlass-base-dev, gcc, gfortran, g++, build-essential, libtool, automate
# libewf requires: bison, flex, zlib1g-dev, libtalloc2, libtalloc-dev
# pyewf requires: python, python-dev, python-pip
# postgres requires: postgresql, pgadmin3, postgresql-server-dev-10
# pylucene: openjdk-8-*, ant-*, ivy-*
# Text extraction: antiword, poppler-utils
# textract: python-dev libxml2-dev libxslt1-dev antiword unrtf poppler-utils pstotext tesseract-ocr flac ffmpeg lame libmad0 libsox-fmt-mp3 sox libjpeg-dev zlib1g-dev
#

install_ubuntu_packages() {
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
g++-5
gcc
gcc-5
gfortran
git
ivy
ivy-doc
jcc
lame
libatlas-base-dev
libffi-dev
libjpeg-dev
liblzma-dev
libmad0
libtalloc2
libtalloc-dev
libpcre3
libpcre3-dev
libpulse-dev
libsox-fmt-mp3
libtool
libxml2-dev
libxslt1-dev
lzma
nginx
odt2txt
openjdk-8-jdk
openjdk-8-jre-headless
pgadmin3
poppler-utils
postgresql
postgresql-server-dev-10
pstotext
python
python-pip
python-dev
python3-pip
python3-dev
python-virtualenv
rabbitmq-server
redis-server
sox
subversion
swig
swig3.0
tesseract-ocr
virtualbox-guest-utils
virtualenv
virtualenvwrapper
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

install_ubuntu_pip_packages() {

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
        pdfminer
        python-magic
        textract
        spacy
        shortuuid"

    pip_special_packages="textacy"

    source "$BCAW_ROOT/venv/bin/activate"

    if [ "$@" = "dev" ]; then
        pip_packages="$pip_packages"
    elif [ "$@" = "stable" ]; then
        pip_packages="$pip_packages"
    fi

    ERROR=0

    for PACKAGE in $pip_packages; do
        CURRENT_ERROR=0
        echoinfo "Installed Python Package: $PACKAGE"
        __pip_install_noinput $PACKAGE >> $LOG_BASE/bca-install.log 2>&1 || (let ERROR=ERROR+1 && let CURRENT_ERROR=1)
        if [ $CURRENT_ERROR -eq 1 ]; then
            echoerror "Python Package Install Failure: $PACKAGE"
        fi
    done

    # Clean pip cache
    rm -rf ~/.cache/pip

    # Prep environment for special packages, install cld2-cffi
    env CC=/usr/bin/gcc-5 pip3 install -U cld2-cffi

    for PACKAGE in $pip_special_packages; do
        CURRENT_ERROR=0
        echoinfo "Installed Python (special setup) Package: $PACKAGE"
        __pip_pre_install_noinput $PACKAGE >> $LOG_BASE/bca-install.log 2>&1 || (let ERROR=ERROR+1 && let CURRENT_ERROR=1)
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

    echoinfo "bitcurator-access-webtools: Setting JAVA_HOME and JCC_JDK"
    export JAVA_HOME=/usr/lib/jvm/java-8-openjdk-amd64
    export JCC_JDK=/usr/lib/jvm/java-8-openjdk-amd64

    # Install pylucene (also installs JCC)
    echoinfo "bitcurator-access-webtools: Building and installing pylucene"
    echoinfo " -- This may take several minutes..."

        cd /tmp
        wget https://archive.apache.org/dist/lucene/pylucene/pylucene-8.3.0-src.tar.gz >> $LOG_BASE/bca-install.log 2>&1
        tar -zxvf pylucene-8.3.0-src.tar.gz >> $LOG_BASE/bca-install.log 2>&1
        cd pylucene-8.3.0
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
        grep -A 8 "Debian Jessie 64-bit, Python 2" Makefile | sed -n '4,8p' | sed 's/^#//' > temp
        #sed -i "s/PREFIX_PYTHON=\/usr/PREFIX_PYTHON=\/var\/www\/bcaw\/venv/g" temp
        sed -i "s/PREFIX_PYTHON=\/opt\/apache\/pylucene\/_install/PREFIX_PYTHON=\/var\/www\/bcaw\/venv/g" temp
        sed -i "s/ANT=JAVA_HOME=\/usr\/lib\/jvm\/java-8-oracle/ANT=JAVA_HOME=\/usr\/lib\/jvm\/java-8-openjdk-amd64/g" temp
        sed -i -e '/Debian Jessie 64-bit, Python 2/r temp' Makefile

        # Finally, remove the shared flag for the time being. See
        # http://lucene.apache.org/pylucene/jcc/install.html for why the shared
        # flag is used. Setuptools in 14.04LTS is not properly patched for this right now.
        sed -i "s/JCC=\$(PYTHON)\ -m\ jcc\ --shared/JCC=\$(PYTHON)\ -m\ jcc/g" Makefile

        make >> $LOG_BASE/bca-install.log 2>&1
        sudo make install |& sudo tee -a $LOG_BASE/bca-install.log
        sudo ldconfig
        # Clean up
        # rm -rf /tmp/pylucene-8.3.0*

  # Checking postgres setup
  echoinfo "bitcurator-access-webtools: Checking postgres setup"
        cd /tmp
        check_install postgresql postgresql >> $LOG_BASE/bca-install.log 2>&1

  # Starting postgres
  echoinfo "bitcurator-access-webtools: Starting postgres service and creating DB"
        # Start postgress and setup up postgress user
        # See: http://askubuntu.com/questions/810008/after-upgrade-14-04-to-16-04-1-postgresql-server-does-not-start
        sudo service postgresql start

        # Create the database bca_db with owner vagrant
        # Create user first
  echoinfo "bitcurator-access-webtools: Creating postgres user"
        sudo -u postgres psql -c"CREATE user vagrant WITH PASSWORD 'vagrant'"

        # Create the database
  echoinfo "bitcurator-access-webtools: Creating bca_db database"
        sudo -u postgres createdb -O vagrant bca_db

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

  # Install The Sleuth Kit
  echoinfo "bitcurator-access-webtools: Building and installing The Sleuth Kit..."
        cd /tmp
	wget https://github.com/sleuthkit/sleuthkit/archive/sleuthkit-4.4.1/sleuthkit-4.4.1.tar.gz -O sleuthkit-4.4.1.tar.gz >> $LOG_BASE/bca-install.log 2>&1
        tar zxvf sleuthkit-4.4.1.tar.gz >> $LOG_BASE/bca-install.log 2>&1
        cd sleuthkit-sleuthkit-4.4.1

	# Note: as of 1/23/2019 all existing Sleuthkit releases have a reference
	# to a non-ssl Ivy download url that no longer exists. Replace relevant
	# link with sed for now
        cd bindings/java
        sed -i "s/http:\/\/repo2.maven.org/https:\/\/repo1.maven.org/g" build.xml
        sed -i 's/<ibiblio name="central" m2compatible="true"/<ibiblio name="central" m2compatible="true" root="https:\/\/repo1.maven.org\/maven2"\/>/' ivysettings.xml
        cd ../../

        ./bootstrap >> $LOG_BASE/bca-install.log 2>&1
        ./configure >> $LOG_BASE/bca-install.log 2>&1
        make >> $LOG_BASE/bca-install.log 2>&1
        sudo make install |& sudo tee -a $LOG_BASE/bca-install.log
        sudo ldconfig
        # Clean up
        rm /tmp/sleuthkit-4.4.1.tar.gz
        rm -rf /tmp/sleuthkit-sleuthkit-4.4.1

  # Install TSK Python bindings
  echoinfo "bitcurator-access-webtools: Building and installing pytsk..."
        cd /tmp
        cp /vagrant/externals/pytsk-20160111-1.tar.gz .
        tar zxvf pytsk-20160111-1.tar.gz >> $LOG_BASE/bca-install.log 2>&1
        cd pytsk
        "$BCAW_ROOT/venv/bin/python" setup.py build >> $LOG_BASE/bca-install.log 2>&1
        #python setup.py build >> $LOG_BASE/bca-install.log 2>&1
        #sudo python setup.py install >> $LOG_BASE/bca-install.log 2>&1
        # Modified for use in virtualenv
        "$BCAW_ROOT/venv/bin/python" setup.py install >> $LOG_BASE/bca-install.log 2>&1

        # Clean up
        rm -rf /tmp/pytsk
}

get_spacy_language_models() {
  echoinfo "bitcurator-access-webtools: Getting language model(s) for spacy..."
  cd /tmp
  source "$BCAW_ROOT/venv/bin/activate"
  python -m spacy download en
}

install_dfvfs() {
  echoinfo "bitcurator-access-webtools: Getting dfvfs requirements and installing dfvfs..."
  cd /tmp
  curl -O https://raw.githubusercontent.com/log2timeline/dfvfs/master/requirements.txt
  pip install -r requirements.txt
  pip install dfvfs
}

create_virtualenv() {
  echoinfo "bitcurator-access-webtools: Creating and activating Python virtualenv..."
  if [ -d "$WWW_ROOT" ]; then
  	rm -rf "$WWW_ROOT"
  fi
  mkdir -p "$WWW_ROOT"
  mkdir -p "$BCAW_ROOT"
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

  # This cp will only succeed in 16.04LTS builds
  cp -f "$SOURCE_ROOT/"*.service /etc/systemd/system

  chown www-data:www-data "$BCAW_ROOT/"*.py
  chown -R www-data:www-data "$BCAW_TARGET"
  cp -r "$CONF_SOURCE" "$BCAW_ROOT"
  chown -R www-data:www-data "$CONF_TARGET"
}

copy_disk_images() {
  echoinfo "bitcurator-access-webtools: Copying disk images from source..."

  # App should be architected to avoid copying. Should set up shared folder(s)
  # with host and point there. Performance issues?
  # For now, this...
  cp -r "$DISK_IMAGE_SOURCE" "$BCAW_ROOT"
  chown -R www-data:www-data "$DISK_IMAGE_TARGET"
  # Updated to properly handle subdirectories and files, be less permissive
  find "$DISK_IMAGE_TARGET" -type d -exec chmod 775 {} \;
  find "$DISK_IMAGE_TARGET" -type f -exec chmod 664 {} \;

  # Previously did this:
  #chmod 777 "$DISK_IMAGE_TARGET"
  #chmod 666 "$DISK_IMAGE_TARGET/"*
}

run_indexer() {
  # Webapp will crash attempting to create GROUP table if accessed before first indexer/analyser run
  echoinfo "bitcurator-access-webtools: About to run indexer/analyser for the first time."
  /vagrant/scripts/index_collections.sh >> $LOG_BASE/bca-install.log 2>&1 || return 1
}

configure_webstack() {
  echoinfo "bitcurator-access-webtools: Configuring BCA Webtools web stack..."

   # Temporary: Create and perm-fix log file
  echoinfo "bitcurator-access-webtools: Preparing log files"
  sudo touch /var/log/bcaw.log
  sudo chmod 666 /var/log/bcaw.log
  sudo touch /var/log/bcaw-analyser.log
  sudo chmod 666 /var/log/bcaw-analyser.log

  if [ -d "$WWW_ROOT/run" ]; then
    rm -rf "$WWW_ROOT/run"
  fi

   mkdir -p "$WWW_ROOT/run"
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

   # Start and enable bcaw
   systemctl start bcaw
   systemctl enable bcaw 2>&1 

   # Start UWSGI and NGINX
   #if [ $VER == "17.04" ]; then
   echoinfo "bitcurator=access-webtools: Restarting nginx (via systemctl)";
   systemctl restart nginx
   echoinfo "bitcurator-access-webtools: Starting usgi (via systemctl)";
   systemctl start uwsgi
   #fi

   # Give vagrant user access to www-data
   usermod -a -G www-data vagrant

   # Set up the cache + index directory
   mkdir -p "$CACHE_DIR"
   chown www-data:www-data "$CACHE_DIR"

   mkdir -p "$LUCENE_INDEX"

   chmod 775 "$LUCENE_INDEX"
   chown www-data:www-data "$LUCENE_INDEX"

   # Add the image indexing script to the chrontab
   sudo -u vagrant crontab -l 2>/dev/null > /tmp/cron || true # Suppress error message on normal condition where no crontab exists
   sudo -u vagrant echo "0 17 * * sun /vagrant/scripts/index_collections.sh" >> /tmp/cron
   sudo -u vagrant crontab /tmp/cron
   rm /tmp/cron
   sudo -u vagrant -H nohup /vagrant/scripts/index_collections.sh &>/dev/null &

}

complete_message() {
    echo
    echo "Installation Complete!"
    echo
}

OS=$(lsb_release -si)
ARCH=$(uname -m | sed 's/x86_//;s/i[3-6]86/32/')
VER=$(lsb_release -sr)

if [ $OS != "Ubuntu" ]; then
    echo "bitcurator-access-webtools is only installable on the Ubuntu operating system at this time."
    exit 1
fi

#if [ $VER != "XX.XX" ]; then
#    echo "bitcurator-access-webtools is only installable on Ubuntu XX.XX at this time."
#    exit 3
#fi

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
echoinfo "OS: $OS"
echoinfo "Arch: $ARCH"
echoinfo "Version: $VER"
echoinfo "The current user is: $SUDO_USER"

export DEBIAN_FRONTEND=noninteractive

# Install all dependencies and apt packages
#install_ubuntu_${VER}_deps $ITYPE
#install_ubuntu_${VER}_packages $ITYPE
install_ubuntu_deps $ITYPE
install_ubuntu_packages $ITYPE

# Prepare the virtualenv
create_virtualenv

# Pip packages and source builds
#install_ubuntu_${VER}_pip_packages $ITYPE
install_ubuntu_pip_packages $ITYPE
install_source_packages

# Get langauge model(s) for NLP tasks
get_spacy_language_models

# Digital Forensics Virtual File System suite install
# install_dfvfs

# Copy over disk images
# copy_disk_images

copy_source

run_indexer

configure_webstack

complete_message
