# This file contains items that can be configured in DIMAC.
#
# IMAGEDIR - the local directory containing your disk images
# SQLALCHEMY_DATABASE_URI - the local db URI (you must configure a postgres
#                           database before running the main script.

IMAGEDIR = "/home/bcadmin/disk_images"
SQLALCHEMY_DATABASE_URI = "postgresql://bcadmin:bcadmin@localhost/bcdb"
