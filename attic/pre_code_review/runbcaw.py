#!/usr/bin/python
# coding=UTF-8
#
# BitCurator Access Webtools (Disk Image Access for the Web)
#
# This code is distributed under the terms of the GNU General Public
# License, Version 3. See the text file "COPYING" for further details
# about the terms of this license.
#
# This script starts the main application server. It is called by
# the servstart.sh bash script (in the provision directory) which is
# run each time the Vagrant machine is brought up.
#

from bcaw import app as application

application.debug=True

if __name__ == "__main__":
	application.run('0.0.0.0')