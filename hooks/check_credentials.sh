#! /bin/bash
#
# check_credentials.sh [username] [password]
# Return 0 if authentification OK, or not 0 if failed.
# FORK THIS GIT REPOSITORY AND EDIT THIS FILE
# Sample usage: Go query a Mysql database or ask one REST API somewhere
#

# Sample code to be replaced
if [ "$1" == "nand" -a "$2" == "booyah" ]; then
  exit 0
fi

exit 1