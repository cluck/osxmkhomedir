# OS X mkhomedir help scripts

This is a command line utility for OS X that that installs itself to run
upgrade and login scripts during the users' login process.

This allows the Administrator to install scripts under
/usr/local/Library/osxmkhomedir that are either run once per user to *upgrade*
the user's profile or then at every login. Scripts can be run both with
administrative privileges and under the users' privileges.

The scripts are left as an exercise to the Administrator and must be installed
to /usr/local/Library/osxmkhomedir.  Permissions on this directory and the
scripts are important. Under no circumstance should a script or program be
called that the user could have modified, as this enables the user to take full
control of the system. The scripts are ignored if not both the directory and
the scripts are owned by the user root and by the group admin and not writable
to other users. The Administrator's scripts should take similar precautions to
avoid system compromise.

Scripts that are supposed to be run once per user (user profile) are *upgrade*
scripts, and carry a *revision* (N) in their name. They are supposed to
transform a user's profile from the previous revision (N-1) to the current
revision (N).  All necessary upgrade scripts are called in sequence,
alternating the administrative privileged to the non-privileged scripts.
When all upgrade scripts were run successfully, the *login* scripts are run.

* /usr/local/Library/osxmkhomedir
  * upgrade<N>-privileged.sh - runs as user root when the user profile is of lower revision
  * upgrade<N>.sh - runs as the logging in user when the user profile is of lower revision
  * login-privileged.sh - runs as user root when the user logs in, after possible upgrade scripts
  * login.sh - runs as the logging in user, after possible upgrade scripts

The scripts must terminate with a non-zero exit code to signal error
conditions.  Calling of upgrade scripts is interrupted and will be retried
during the next login. Login scripts will not be run if any of the upgrade
scripts signals an error condition.

All scripts are called with two arguments, the username and the home directory.
```sh
[login|upgrade<N>][-privileged].sh <username> <user-home-directory>
```

## Installation

```sh
su -
easy_install pip
pip install git+git://github.com/cluck/osxmkhomedir.git
osxmkhomedir --install
```

