microgit-server
===============

A micro ssh git server with external, customisable authentification.
It supports both SSH keys and password authentification, and it does not require you to have one unix account per user.
You provide the scripts that return the public SSH keys of users and check their credentials.

Sample usage: Plug it to your Mysql database, or to your REST API.

TODO: Expands infos.

Credits
=======
Heavily based on https://github.com/bshi/blag-examples/