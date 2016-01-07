BitCurator Access Webtools: Disk Image Access for the Web
------------------------------------
The bca-webtools project allows users to browse a wide range of file systems contained within
disk images using a web browser. It is intended to support access requirements in libraries,
archives, and museums preserving born-digital materials extracted from source media as raw or
forensically-packaged disk images. 

BCA-Webtools uses open source libraries and toolkits including The Sleuth Kit, PyTSK, and 
the Flask web microservices framework. It uses PyLucene along with format-specific text-extraction
tools to index the contents of files contained in disk images, allowing users to search for
relevant content without individually inspecting files.

BCA-Webtools is distributed with a simple build script that deploys it as a Vagrant virtual
machine running the web service. It includes several sample images (in the "disk-images" directory)
to get you started.

Find out more at <http://access.bitcurator.net/>

See a previous version of bca-webtools (DIMAC) in action at <http://www.youtube.com/watch?v=BwiWFqxYzQ8>.

# Getting started
This software uses Vagrant to provision a virtual machine in which bca-webtools runs. To start, make sure you have VirtualBox installed:

  * http://www.virtualbox.org/

and Vagrant installed:

  * https://vagrantup.com

You can download the latest release of the bca-webtools application here:

  * https://github.com/BitCurator/bca-webtools/releases

(or, if you'd like to test the development branch, you can check the current commit out directly):

  * git clone https://github.com/bitcurator/bca-webtools

Once you have the source code (and you have unzipped it if you're using a release), change directory into bca-webtools, and make sure the associated Vagrant box (ubuntu/trusty64) is added:

  * cd bca-webtools
  * vagrant box add ubuntu/trusty64

The first time you run "vagrant box add ubuntu/trusty64" may take some time. Updates to the base vagrant box (a headless Ubuntu environment) are generally issued every couple of weeks. Vagrant will warn you when your box is out of date. (Note: You only need to run the "vagrant box add" the first time after installing Vagrant. You may be promted to run the command "vagrant box update" in future sessions, however, in order to keep the box up to date).

The bca-webtools application can be used to view raw (.dd) and EWF (.E01) images containing FAT16, FAT32, NTFS, ext2/3/4, and HFS+ file systems. The application includes two sample images (in the bca-webtools/disk-images directory) for testing. You can place additional images in this directory (and remove these test images) as needed.

Once the base box is downloaded, you can start the service by running the command: 

  * vagrant up

from within the bca-webtools directory. This step can take a long time the first time you run the software (15-30 minutes depending on your computer). The installation script will provide feedback in the console as it installs each package. Once the virtual machine has been provisioned, open a web browser on your host and navigate to:

  * 127.0.0.1:8080

to see the bca-webtools service running. 

# Browsing and Searching

IMPORTANT! In the current release, a searchable index of the filenames and file system contents must be generated prior to using the "Search" bar on the right hand side of the window. 

Click on the "Admin" link at the bottom left of the window, and do the following:

  * Select "Build DFXML Table", and click "Submit". This is required for filename search to work.

  * Next, select "Generate Index", and click "Submit". The index generation process may take some time. It will run in the background; you can navgate away from the index page once you see the "Index being built" message. 

# Terminating the bca-webtools service and virtual machine

If you need to stop the service, you can type:

  * vagrant halt

in the console on your host machine. The next time you issue the "vagrant up" command, the VM will restart in its previous state. If you need to delete the VM entirely, you can issue a "vagrant destroy" command after "vagrant halt".

# Dependencies

The bca-webtools project is a Flask application that is deployed automatically into an appropriately configured Ubuntu 14.04LTS virtual machine. It has been tested with Python 2.7.3, Flask 0.11, Jinja2, and Postgres 9.3 (but will likely work with other versions). Python 3 should also work.
Several other libraries and tools are required, including AFFLIB (v3.7.4 or later), libewf (20140427 or later), The Sleuth Kit (4.1.3 or later), and PyTSK.

Some of these dependencies have existing apt or pip packages in Ubuntu. Others do not. To simplify the process, we've written a bootstrap script that updates and upgrades all the necessary packages, compiles and installs the necessary source packages, and sets up the database. This script is located in the provision directory, and is only run the first time you execute the "vagrant up" command.

# bca-webtools Documentation

More documentation coming soon. bca-webtools is currently in alpha; updates will be posted here and on our website at [http://access.bitcurator.net/](http://access.bitcurator.net/) as they become available.

# License(s)

bca-webtools project documentation, and other non-software products of the BitCurator Access team are subject to the the Creative Commons Attribution 3.0 Unported license (CC BY 3.0).

Unless otherwise indicated, software objects in this repository are distributed under the terms of the GNU General Public License, Version 3. See the text file "LICENSE" for further details about the terms of this license.


