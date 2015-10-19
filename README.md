BitCurator Access Webtools: Disk Image Access for the Web
------------------------------------
The bca-webtools project provides simple access to disk images over the web using open source 
software including The Sleuth Kit, PyTSK, the Flask web framework, and postgres.

Simply point bca-webtools at a local directory that contains raw (dd) or forensically-packaged disk 
images, and it will create a web portal that allows you to browse the file systems, download 
files, and examine disk image metadata.

Find out more at <http://access.bitcurator.net/>

See a previous version of bca-webtools (DIMAC) in action at <http://www.youtube.com/watch?v=BwiWFqxYzQ8>.

# Getting started
This software uses Vagrant to provision a virtual machine in which bca-webtools runs. To start, make sure you have VirtualBox installed:

  * http://www.virtualbox.org/

and Vagrant installed:

  * https://vagrantup.com

To check out the bca-webtools code repo, run:

  * git clone https://github.com/bitcurator/bca-webtools

Once you have this repository cloned, make sure the associated Vagrant box (ubuntu/trusty64) is up to date:

  * cd bca-webtools
  * vagrant box update

You can then start the service by running the command: 

  * vagrant up

from within the bca-webtools directory. There's a sample image in the "disk-images" directory to get you started. Once the virtual machine has been provisioned, open a web browser on your host and navigate to:

  * 127.0.0.1:8080

to see the bca-webtools service running.

# Dependencies

The bca-webtools project is a Flask application. It has been tested with Python 2.7.3, Flask 0.11, Jinja2, and Postgres 9.3 (but will likely work with other versions). Python 3 should also work.
You'll also need several other libraries and tools, including AFFLIB (v3.7.4 or later), libewf (20140427 or later), The Sleuth Kit (4.1.3 or later), and PyTSK.

On a Debian or Ubuntu system, some of these dependencies are simply apt packages. Others are a bit more involved, as the required versions are not packaged. To simplify the process, we've written a bootstrap script that updates and upgrades all the necessary packages, compiles and installs the necessary source packages, and sets up the database. This script is located in the provision directory, and is only run the first time you execute the "vagrant up" command.

# bca-webtools Documentation

More documentation coming soon. bca-webtools is currently in alpha; updates will be posted here and on our website at [http://access.bitcurator.net/](http://access.bitcurator.net/) as they become available.

# License(s)

bca-webtools project documentation, and other non-software products of the BitCurator Access team are subject to the the Creative Commons Attribution 3.0 Unported license (CC BY 3.0).

Unless otherwise indicated, software objects in this repository are distributed under the terms of the GNU General Public License, Version 3. See the text file "COPYING" for further details about the terms of this license.


