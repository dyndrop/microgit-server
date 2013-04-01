microgit-server
===============

A micro ssh git server with external, customisable authentification.
It supports both SSH keys and password authentification, and it does not require you to have one unix account per user.
You provide the scripts that return the public SSH keys of users and check their credentials.

Sample usage: Plug it to your Mysql database, or to your REST API.

Usage
=====

    ./microgit-server.py -i ../path/to/ssh/key -p 2222 -c ./hooks/check_credentials.sh -k ./hooks/get_pub_keys.sh

check_credentials.sh and get_pub_keys.sh located in the hooks folder are dummy scripts that check the user credentials and return their SSH public keys. Please check them to know what the script receive as arguments and what they are supposed to return.

Credits
=======
Based on https://github.com/bshi/blag-examples/