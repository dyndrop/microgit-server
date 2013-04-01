microgit-server
===============

A micro ssh git server with external, customisable authentification.
It supports both SSH keys and password authentification, and it does not require you to have one unix account per user.
You provide the scripts that return the public SSH keys of users, check their credentials, and return the location of the repositories in the filesystem.

Sample usage: Plug this server to your user table in your Mysql database, or to your authentification REST API call.

Usage
=====

    ./microgit-server.py -i ../path/to/ssh/key -p 2222 -c ./hooks/check_credentials.sh -k ./hooks/get_pub_keys.sh -r ./hooks/get_repo_location.sh

 - ./hooks/check_credentials.sh: Dummy script to check if the user login/password is valid.
 - ./hooks/get_pub_keys.sh: Dummy script to return the registered public keys of the user getting logged in (which would usually be stored in ~/.ssh/authorized_keys)
 - ./hooks/get_repo_location.sh: Dummy script that return the physical location of the requested repository in the filesystem. The dummy script use the ./repos folder as location, and create automatically the repositories on demand.

Credits
=======
Based on https://github.com/bshi/blag-examples/