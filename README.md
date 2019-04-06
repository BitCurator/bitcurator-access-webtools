![logo](https://github.com/BitCurator/bitcurator.github.io/blob/master/logos/BitCurator-Basic-400px.png)

# BitCurator Access Webtools: Browse disk images and file system metadata in a web service

[![GitHub issues](https://img.shields.io/github/issues/bitcurator/bitcurator-access-webtools.svg)](https://github.com/bitcurator/bitcurator-access-webtools/issues)
[![GitHub forks](https://img.shields.io/github/forks/bitcurator/bitcurator-access-webtools.svg)](https://github.com/bitcurator/bitcurator-access-webtools/network)
[![Build Status](https://travis-ci.org/BitCurator/bitcurator-access-webtools.svg?branch=master)](https://travis-ci.org/BitCurator/bitcurator-access-webtools)
[![Twitter Follow](https://img.shields.io/twitter/follow/bitcurator.svg?style=social&label=Follow)](https://twitter.com/bitcurator)

The **BitCurator Access Webtools** project allows users to browse file systems contained within disk images using a web browser. It is intended to support access requirements in libraries, archives, and museums preserving born-digital materials extracted from source media as raw or forensically-packaged disk images. 

The service uses open source libraries and toolkits including The Sleuth Kit, PyTSK, and the Flask web microservices framework. It uses PyLucene along with format-specific text-extraction tools to index the contents of files contained in disk images, allowing users to search for relevant content without individually inspecting files.

This repository includes a simple build script that deploys the web service as in a VirtualBox VM using Vagrant. It includes several sample images (in the "disk-images" directory) to get you started.

Find out more at https://github.com/BitCurator/bitcurator-access/wiki

## Getting started
This software uses Vagrant to provision a virtual machine in which **bitcurator-access-webtools** runs. To start, make sure you have VirtualBox and Vagrant installed on your Windows, Mac, or Linux host:

  * http://www.virtualbox.org/
  * https://vagrantup.com

Clone this repository with the following command in a terminal or command shell (Need help installing git? See the **How to install a git client** section at the bottom of this page):

```shell
git clone https://github.com/bitcurator/bitcurator-access-webtools
```

Once you've checked out the source, change directory into bitcurator-access-webtools, and make sure the associated Vagrant box (bentu/ubuntu-18.04) is added:

```shell
cd bitcurator-access-webtools
vagrant box add bento/ubuntu-18.04
```

You will be prompted for a provider. Select **3) virtualbox** by typing '3' and hitting enter.

The first time you run **vagrant box add bento/ubuntu-18.04** may take some time. (Note: You only need to run **vagrant box add** for a particular box one time after installing Vagrant. You may be promted to run the command **vagrant box update** in future sessions in order to keep the box up to date).

The bitcurator-access-webtools application can be used to view raw (.dd) and EWF (.E01) images containing FAT16, FAT32, NTFS, ext2/3/4, and HFS+ file systems. The application includes several sample images (in the **bitcurator-access-webtools/disk-images** directory) for testing. You can place additional images in this directory (and remove these test images) as needed.

Once the base box is downloaded, you can start the service by running the command: 

```shell
vagrant up
```

from within the bitcurator-access-webtools directory. This step can take a long time the first time you run the software (15-30 minutes depending on your computer). The installation script will provide feedback in the console as it installs each package. Once the virtual machine has been provisioned, open a web browser on your host and navigate to:

```shell
127.0.0.1:8080
```

to see the **bitcurator-access-webtools** service running.

## Terminating the bitcurator-access-webtools service and virtual machine

If you need to stop the service, you can type:

```shell
vagrant halt
```

in the **bitcurator-access-webtools** directory in the console or terminal on your host machine. The next time you issue the "vagrant up" command, the VM will restart in its previous state. 

If you need to delete the VM entirely, you can the the following command after halting the VM:

```shell
vagrant destroy
```

If you wish to build a new VM with updated sources, simply delete the bitcurator-access-webtools directory after halting and destroying the previous VM, and clone or download the current sources from GitHub.

## Dependencies

This is a Flask application that is deployed automatically into an appropriately configured Ubuntu 18.04 virtual machine. It has been tested with Python 2.7.3, Flask 0.11, Jinja2, and Postgres 9.3 (but will likely work with other versions). Python 3 should also work.
Several other libraries and tools are required, including AFFLIB (v3.7.4 or later), libewf (20140427 or later), The Sleuth Kit (4.1.3 or later), and PyTSK.

Some of these dependencies have existing apt or pip packages in Ubuntu. Others do not. To simplify the process, we've written a bootstrap script that updates and upgrades all the necessary packages, compiles and installs the necessary source packages, and sets up the database. This script is located in the provision directory, and is only run the first time you execute the **vagrant up** command.

## Documentation

The latest documentation can be found on the BitCurator Access wiki page at https://github.com/BitCurator/bitcurator-access/wiki.

Or, follow this link to a direct download of the quick start guide:

http://distro.ibiblio.org/bitcurator/docs/BCA-Quickstart.pdf

## License(s)

The BitCurator logo, BitCurator project documentation, and other non-software products of the BitCurator team are subject to the the Creative Commons Attribution 4.0 Generic license (CC By 4.0).

Unless otherwise indicated, software items in this repository are distributed under the terms of the GNU General Public License, Version 3. See the text file "COPYING" for further details about the terms of this license.

In addition to software produced by the BitCurator team, BitCurator packages and modifies open source software produced by other developers. Licenses and attributions are retained here where applicable.

## How to install a git client

On **Windows**, download and install git from:

  * https://git-scm.com/downloads

On **MacOS**, run the following command in a terminal and click through the prompts:

```shell
xcode-select --install
```

On Debian-based variants of Linux (including Ubuntu), run the following from a terminal:

```shell
sudo apt-get install git
```

**IMPORTANT**: On Windows, you **must** make Git check out files with Unix-style line endings in order for the VM to run properly. After installing git, run the following in a console (cmd prompt):

```shell
git config --global core.autocrlf false
```
