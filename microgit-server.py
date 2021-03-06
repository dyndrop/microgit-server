#!/usr/bin/env python
import os
import shlex
import sys
import subprocess
from optparse import OptionParser
from twisted.conch.avatar import ConchUser
from twisted.conch.checkers import SSHPublicKeyDatabase
from twisted.conch.checkers import UNIXPasswordDatabase
from twisted.conch.error import ConchError
from twisted.conch.ssh import common
from twisted.conch.ssh.session import (ISession,
                                       SSHSession,
                                       SSHSessionProcessProtocol)
from twisted.conch.ssh.factory import SSHFactory
from twisted.conch.ssh.keys import Key
from twisted.cred.portal import IRealm, Portal
from twisted.cred.error import UnauthorizedLogin, UnhandledCredentials
from twisted.internet import reactor
from twisted.internet import defer
from twisted.python import components, log
from zope import interface
log.startLogging(sys.stderr)


class IGitMetadata(interface.Interface):
    'API for authentication and access control.'

    def repopath(self, username, reponame):
        '''
        Given a username and repo name, return the full path of the repo on
        the file system.
        '''

    def get_pub_keys(self, username):
        '''
        Given a username return a list of OpenSSH compatible public key
        strings.
        '''

    def check_credentials(self, username, password):
        '''
        Given a username and a password return whether they are valid.
        '''


class BallinMockMeta(object):
    'Mock persistence layer.'
    interface.implements(IGitMetadata)

    def set_scripts(self, public_keys_script, check_credentials_script, repo_location_script):
        self.public_keys_script = public_keys_script
        self.check_credentials_script = check_credentials_script
        self.repo_location_script = repo_location_script

    def repopath(self, username, reponame):
        result = subprocess.Popen([self.repo_location_script, reponame, username],stdout=subprocess.PIPE).communicate()[0]
        if result == "":
            result = None 
        return result

    def get_pub_keys(self, username):
        keys = subprocess.Popen([self.public_keys_script, username],stdout=subprocess.PIPE).communicate()[0]
        return keys.split('\n')

    def check_credentials(self, username, password):
        result = subprocess.call([self.check_credentials_script, username, password])
        return (result == 0)

def find_git_shell():
    # Find git-shell path.
    # Adapted from http://bugs.python.org/file15381/shutil_which.patch
    path = os.environ.get("PATH", os.defpath)
    for dir in path.split(os.pathsep):
        full_path = os.path.join(dir, 'git-shell')
        if (os.path.exists(full_path) and 
                os.access(full_path, (os.F_OK | os.X_OK))):
            return full_path
    raise Exception('Could not find git executable!')


class GitSession(object):
    interface.implements(ISession)

    def __init__(self, user):
        self.user = user

    def execCommand(self, proto, cmd):
        argv = shlex.split(cmd)
        reponame = argv[-1]
        sh = self.user.shell

        # Check permissions by mapping requested path to file system path
        repopath = self.user.meta.repopath(self.user.username, reponame)
        if repopath is None:
            raise ConchError('Invalid repository.')
        command = ' '.join(argv[:-1] + ["'%s'" % (repopath,)])
        reactor.spawnProcess(proto, sh,(sh, '-c', command))

    def eofReceived(self): pass

    def closed(self): pass


class PatchedSSHSession(SSHSession):

    #
    # If you don't add these two method overrides, if a user import quite some
    # data (e.g. clone big repos), and the remote window and the local 
    # outgoing data buffer is filled, SSHSession seems to be discarding 
    # the remaining data.  As a result, you get random errors like:
    # 
    # $ git clone xxxxxx
    # Cloning into 'booyah12'...
    # remote: Counting objects: 1154, done.
    # remote: Compressing objects: 100% (1139/1139), done
    # Receiving objects: 72%
    # fatal: The remote end hung up unexpected
    # fatal: early EOFs:
    # fatal: index-pack failed

    def stopWriting(self):
        self.client.transport.pauseProducing()
 
    def startWriting(self):
        self.client.transport.resumeProducing()


class GitConchUser(ConchUser):
    shell = find_git_shell()

    def __init__(self, username, meta):
        ConchUser.__init__(self)
        self.username = username
        self.channelLookup.update({"session": PatchedSSHSession})
        self.meta = meta

    def logout(self): pass


class GitRealm(object):
    interface.implements(IRealm)

    def __init__(self, meta):
        self.meta = meta

    def requestAvatar(self, username, mind, *interfaces):
        user = GitConchUser(username, self.meta)
        return interfaces[0], user, user.logout


class GitPubKeyChecker(SSHPublicKeyDatabase):
    def __init__(self, meta):
        self.meta = meta

    def checkKey(self, credentials):
        for k in self.meta.get_pub_keys(credentials.username):
            if k != "" and Key.fromString(k).blob() == credentials.blob:
                return True
        return False

class GitPasswordChecker(UNIXPasswordDatabase):
    def __init__(self, meta):
        self.meta = meta

    def requestAvatarId(self, credentials):
        if self.meta.check_credentials(credentials.username, credentials.password):
            return defer.succeed(credentials.username)
        return defer.fail(UnauthorizedLogin("unable to verify password"))


class GitServer(SSHFactory):
    authmeta = BallinMockMeta()
    portal = Portal(GitRealm(authmeta))
    portal.registerChecker(GitPubKeyChecker(authmeta))
    portal.registerChecker(GitPasswordChecker(authmeta))

    def __init__(self, server_privkey, public_keys_script, check_credentials_script, repo_location_script):
        pubkey = '.'.join((server_privkey, 'pub'))
        self.privateKeys = {'ssh-rsa': Key.fromFile(server_privkey)}
        self.publicKeys = {'ssh-rsa': Key.fromFile(pubkey)}

        self.authmeta.set_scripts(public_keys_script, check_credentials_script, repo_location_script)


if __name__ == '__main__':

    usage = "usage: %prog [options]"
    parser = OptionParser(usage=usage)
    parser.add_option("-c", "--check-credentials-script", dest="check_credentials_script",
        help="FILE is to be executed to check credentials of a user",
        metavar="FILE")
    parser.add_option("-i", "--identity-file", dest="server_identity_file",
        help="Use FILE as the SSH identity file of the server [default: %default]", 
        metavar="FILE",
        default="~/.ssh/id_rsa")
    parser.add_option("-k", "--public-keys-script", dest="public_keys_script",
        help="FILE is to be executed to return the public keys of a user",
        metavar="FILE")
    parser.add_option("-p", "--port", type="int", dest="port", default=22,
        help="The port number of the server [default: %default]")
    parser.add_option("-r", "--repo-location-script", dest="repo_location_script",
        help="FILE is to be executed to return the filesystem path of a requested repository",
        metavar="FILE")
    (options, args) = parser.parse_args()

    if not options.public_keys_script:
        print "Error: The path to the public keys script is missing."
        sys.exit(1)
    if not os.path.isfile(options.public_keys_script):
        print "Error: The public keys script path is incorrect."
        sys.exit(1)

    if not options.check_credentials_script:
        print "Error: The path to the credentials check script is missing."
        sys.exit(1)
    if not os.path.isfile(options.check_credentials_script):
        print "Error: The credentials check script path is incorrect."
        sys.exit(1)

    if not options.repo_location_script:
        print "Error: The path to the repository location script is missing."
        sys.exit(1)
    if not os.path.isfile(options.repo_location_script):
        print "Error: The repository location script path is incorrect."
        sys.exit(1)

    components.registerAdapter(GitSession, GitConchUser, ISession)
    reactor.listenTCP(options.port, 
        GitServer(os.path.expanduser(options.server_identity_file), 
            options.public_keys_script,
            options.check_credentials_script,
            options.repo_location_script)
        )
    reactor.run()
