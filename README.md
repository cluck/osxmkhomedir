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
called with privileged permissions that the user could have previously modified,
as this enables the user to take full control of the system. The scripts are
ignored if not both the directory and the scripts are owned by the user root
and the group admin, or if other users can write to the directory or the
script. All privileged scripts should take the same precautions to not call
user defined scripts.

Scripts that are supposed to be run once per user (user profile) are *upgrade*
scripts, and carry a *revision* (N) in their name. They are supposed to
transform a user's profile from the previous revision (N-1) to the current
revision (N).  All necessary upgrade scripts are called in sequence,
alternating the administrative privileged to the non-privileged scripts.
When all upgrade scripts were run successfully, the *login* scripts are run,
again first with administrative privileges.

The profile revision is stored in ~/Library/Preferences/ch.cluck.osxmkhomedir.plist.

All scripts are called with two arguments, the username and the home directory.
```sh
[login|upgrade<N>][-privileged].sh <username> <user-home-directory>
```

Example script names under /usr/local/Library/osxmkhomedir, in order of calling:
* upgrade1.sh - runs as logging in user on a newly created profile
* upgrade2-privileged.sh - runs as user root when the user profile is still at revision 1
* upgrade03.sh - runs as the logging in user when the user profile is still at revision 1 or 2
* login-privileged.sh - runs as user root when the user logs in, after possible upgrade scripts
* login.sh - runs as the logging in user, after possible upgrade scripts

The scripts must terminate with a non-zero exit code to signal error
conditions.  Calling of upgrade scripts is interrupted and will be retried
during the next login. Login scripts will not be run if any of the upgrade
scripts signals an error condition.


## Installation

```sh
su -
easy_install pip
pip install git+git://github.com/cluck/osxmkhomedir.git
osxmkhomedir --install
```

