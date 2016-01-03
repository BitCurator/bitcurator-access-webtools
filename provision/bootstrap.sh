#!/usr/bin/env bash

#
# bootstrap.sh: Build and configuration script for bca-webtools in Vagrant
# ------------------------------------------------------------------------
# <http://access.bitcurator.net>
# 
# This bash script provisions the VM, installing and/or compiling the necessary
# forensics and other tools needed to run the bca-webtools Flask application.
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
# See the README for further detais.
#
#===============================================================================
# vim: softtabstop=4 shiftwidth=4 expandtab fenc=utf-8 spell spelllang=en cc=81
#===============================================================================
#
# Needed for Vagrant build
SCRIPT_PATH=$(dirname $(readlink -f $0 ) )

# Base directory for build log
LOG_BASE=/var/log

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
    echo $@ | tr -s '[:space:]' '\n' | awk '!x[$0]++'
}

#--- FUNCTION ----------------------------------------------------------------
# NAME: echoerr
# DESCRIPTION: Echo errors to stderr.
#-------------------------------------------------------------------------------
echoerror() {
    printf "${RC} * ERROR${EC}: $@\n" 1>&2;
}

#--- FUNCTION ----------------------------------------------------------------
# NAME: echoinfo
# DESCRIPTION: Echo information to stdout.
#-------------------------------------------------------------------------------
echoinfo() {
    printf "${GC} * STATUS${EC}: %s\n" "$@";
}

#--- FUNCTION ----------------------------------------------------------------
# NAME: echowarn
# DESCRIPTION: Echo warning informations to stdout.
#-------------------------------------------------------------------------------
echowarn() {
    printf "${YC} * WARN${EC}: %s\n" "$@";
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
    apt-get install -y -o DPkg::Options::=--force-confold $@; return $?
}

#---  FUNCTION  ----------------------------------------------------------------
#          NAME:  __apt_get_upgrade_noinput
#   DESCRIPTION:  (DRY) apt-get upgrade with noinput options
#-------------------------------------------------------------------------------
__apt_get_upgrade_noinput() {
    apt-get upgrade -y -o DPkg::Options::=--force-confold $@; return $?
}

#---  FUNCTION  ----------------------------------------------------------------
#          NAME:  __pip_install_noinput
#   DESCRIPTION:  (DRY)
#-------------------------------------------------------------------------------
__pip_install_noinput() {
    pip install --upgrade $@; return $?
    # Uncomment for Python 3
    #pip3 install --upgrade $@; return $?
}

#---  FUNCTION  ----------------------------------------------------------------
#          NAME:  __pip_install_noinput
#   DESCRIPTION:  (DRY)
#-------------------------------------------------------------------------------
__pip_pre_install_noinput() {
    pip install --pre --upgrade $@; return $?
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
# Bokeh: npm, node
# Celery: celeryd (don't use, deprecated)

install_ubuntu_14.04_packages() {
    packages="dkms 
subversion 
libatlas-base-dev 
gcc 
gfortran 
g++ 
build-essential 
libtool 
automake 
autopoint 
git 
bison 
flex 
python 
python-dev 
python-pip 
zlib1g-dev 
postgresql 
pgadmin3 
postgresql-server-dev-9.3 
libtalloc2 
libtalloc-dev 
antiword 
poppler-utils 
odt2txt
redis-server 
openjdk-7-jdk 
openjdk-7-jre-headless 
openjdk-7-jre-lib 
ant 
ant-doc 
ant-optional 
ivy 
ivy-doc 
rabbitmq-server"

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
celery"

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

  # Install pylucene (also installs JCC)
  echoinfo "bca-webtools: Building and installing pylucene"
  echoinfo " -- This may take several minutes..."
        CDIR=$(pwd)
        cd /tmp
        sudo wget http://apache.mirrors.pair.com/lucene/pylucene/pylucene-4.10.1-1-src.tar.gz >> $LOG_BASE/bca-install.log 2>&1
        tar -zxvf pylucene-4.10.1-1-src.tar.gz >> $LOG_BASE/bca-install.log 2>&1
        cd pylucene-4.10.1-1
        pushd jcc >> $LOG_BASE/bca-install.log 2>&1
        python setup.py build >> $LOG_BASE/bca-install.log 2>&1
        python setup.py install >> $LOG_BASE/bca-install.log 2>&1
        popd >> $LOG_BASE/bca-install.log 2>&1

        # Edit the Makefile to uncomment the config info for Linux.
        # First we look for the requred string in the makefile and copy the 5 lines
        # strting from the 4th line after the pattern match, into a temp file (temp),
        # after removing the leading hash (to uncomment the lines).
        # Then we append these lines from temp file to Makefile after the given pattern
        # is found.
        grep -A 8 "Ubuntu 11.10 64-bit" Makefile | sed -n '4,8p' | sed 's/^#//' > temp
        sed -i -e '/Ubuntu 11.10 64-bit/r temp' Makefile
        make >> $LOG_BASE/bca-install.log 2>&1 
        sudo make install >> $LOG_BASE/bca-install.log 2>&1
        sudo ldconfig
        # Clean up
        cd /tmp
        rm pylucene-4.10.1-1-src.tar.gz
        rm -rf pylucene-4.10.1.-1

  # Checking postgres setup
  echoinfo "bca-webtools: Checking postgres setup"
        CDIR=$(pwd)
        cd /tmp
        check_install postgresql postgresql >> $LOG_BASE/bca-install.log 2>&1

  # Starting postgres
  echoinfo "bca-webtools: Starting postgres service and creating DB"
        # Commented out - not needed currently???
        # .pgpass contains the password for the vagrant user. Needs to be in the home directory.
        #sudo cp /vagrant/.pgpass /home/vagrant/.pgpass

        # Start postgress and setup up postgress user
        sudo service postgresql start

        # Create the database bca_db with owner vagrant
        # Create user first
  echoinfo "bca-webtools: Creating postgres user"
        sudo -u postgres psql -c"CREATE user vagrant WITH PASSWORD 'vagrant'"

        # Create the database
  echoinfo "bca-webtools: Creating bca_db database"
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
  echoinfo "bca-webtools: Building and installing libewf..."
        CDIR=$(pwd)
        cd /tmp
        git clone https://github.com/libyal/libewf >> $LOG_BASE/bca-install.log 2>&1
        cd libewf
        ./synclibs.sh >> $LOG_BASE/bca-install.log 2>&1
        ./autogen.sh >> $LOG_BASE/bca-install.log 2>&1
        ./configure --enable-v1-api --enable-python >> $LOG_BASE/bca-install.log 2>&1
        make >> $LOG_BASE/bca-install.log 2>&1
        sudo make install >> $LOG_BASE/bca-install.log 2>&1
        sudo ldconfig >> $LOG_BASE/bca-install.log 2>&1
        # Clean up
        cd /tmp
        rm -rf libewf
        #sudo wget https://53efc0a7187d0baa489ee347026b8278fe4020f6.googledrive.com/host/0B3fBvzttpiiSMTdoaVExWWNsRjg/libewf-20140608.tar.gz
        #tar -xzvf libewf-20140608.tar.gz
        #cd libewf-20140608
        #bootstrap
        #./configure --enable-v1-api
        #make
        #sudo make install
        #sudo ldconfig

  # Install libqcow (needed for pytsk)
  echoinfo "bca-webtools: Building and installing libqcow..."
        CDIR=$(pwd)
        cd /tmp
        wget https://github.com/libyal/libqcow/releases/download/20150105/libqcow-alpha-20150105.tar.gz >> $LOG_BASE/bca-install.log 2>&1
        tar zxvf libqcow-alpha-20150105.tar.gz >> $LOG_BASE/bca-install.log 2>&1
        cd libqcow-20150105
        ./configure --enable-python >> $LOG_BASE/bca-install.log 2>&1
        make >> $LOG_BASE/bca-install.log 2>&1
        sudo make install >> $LOG_BASE/bca-install.log 2>&1
        sudo ldconfig

  # Install The Sleuth Kit
  echoinfo "bca-webtools: Building and installing The Sleuth Kit..."
        CDIR=$(pwd)
        cd /tmp
        wget https://github.com/sleuthkit/sleuthkit/archive/sleuthkit-4.2.0.tar.gz -O sleuthkit-4.2.0.tar.gz >> $LOG_BASE/bca-install.log 2>&1
        tar zxvf sleuthkit-4.2.0.tar.gz >> $LOG_BASE/bca-install.log 2>&1
        cd sleuthkit-sleuthkit-4.2.0
        ./bootstrap >> $LOG_BASE/bca-install.log 2>&1
        ./configure >> $LOG_BASE/bca-install.log 2>&1
        make >> $LOG_BASE/bca-install.log 2>&1
        sudo make install >> $LOG_BASE/bca-install.log 2>&1
        sudo ldconfig
        # Clean up
        cd /tmp
        rm sleuthkit-4.2.0.tar.gz
        rm -rf sleuthkit-sleuthkit-4.2.0

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

  # Install TSK Python bindings
  echoinfo "bca-webtools: Building and installing pytsk..."
        CDIR=$(pwd)
        cd /tmp
        git clone https://github.com/py4n6/pytsk >> $LOG_BASE/bca-install.log 2>&1
        cd pytsk
        python setup.py build >> $LOG_BASE/bca-install.log 2>&1
        sudo python setup.py install >> $LOG_BASE/bca-install.log 2>&1
        # Clean up
        cd /tmp
        rm -rf pytsk

  # Temporary: Create and perm-fix log file
  echoinfo "bca-webtools: Preparing log file"
        sudo touch /var/log/bcaw.log
        sudo chmod 666 /var/log/bcaw.log

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
    echo "bca-webtools is only installable on Ubuntu operating systems at this time."
    exit 1
fi

#if [ $ARCH != "64" ]; then
#    echo "bca-webtools is only installable on a 64-bit architecture at this time."
#    exit 2
#fi

if [ $VER != "14.04" ]; then
    echo "bca-webtools is only installable on Ubuntu 14.04 at this time."
    exit 3
fi

if [ `whoami` != "root" ]; then
    echoerror "The bca-webtools bootstrap script must run as root."
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

echoinfo "*******************************************************"
echoinfo "The bca-webtools script will now configure your system."
echoinfo "*******************************************************"
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
    install_ubuntu_${VER}_pip_packages $ITYPE
    install_source_packages

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

  # Start the server
  # Reference only - service is no longer started in this script
  # cd /vagrant
  # python runserver.py &

  # Oracle Java 8 silent install
  #sudo apt-get -y -q install software-properties-common htop
  #sudo add-apt-repository -y ppa:webupd8team/java
  #sudo apt-get -y -q update
  #echo oracle-java8-installer shared/accepted-oracle-license-v1-1 select true | sudo /usr/bin/debconf-set-selections
  #echo oracle-java7-installer shared/accepted-oracle-license-v1-1 select true | sudo /usr/bin/debconf-set-selections
  #sudo apt-get -y -q install oracle-java8-installer
  ##apt-get -y -q install oracle-java7-installer
  #sudo update-java-alternatives -s java-8-oracle
  
  # For reference only - download bokeh samples
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
