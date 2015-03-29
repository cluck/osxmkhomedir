# OS X mkhomedir help scripts

This is a command line utility for OS X that installs itself as a launch agent
on OS X, so that it is called when users log in.

Through granting itself password-less sudo rights and storing a preference file in the
users home, it allows for calling additional scripts to act upon user's home directory during login.

Additional scripts are left as an exercise to the Admin and must be installed to /usr/local/Library/osxmkhomedir.
Both this directory and the scripts must be owned by root:admin and other users should not have write access to
the directory and the scripts. If this is not the case osxmkhomedir refuses to launch the scripts.

* /usr/local/Library/osxmkhomedir
  * login-privileged-first.sh - runs as user root when the user logs in for the first time
  * login-privileged.sh - runs as user root when the user logs in, every time, also on the first time
  * login-first.sh - runs as the logging in user when the user logs in for the first time
  * login.sh - runs as the logging in user, every time, also on the first time

The additional scripts are called with the user's environment, and this calling convention:
```sh
/usr/local/Library/osxmkhomedir/login[-privileged][-first].sh <username> <user-home-directory> <revision>
```

The **revision** field is intended for future use; it will indicate the current revision of the
users' home directory. The current script will always pass 1 as the revision.

## Installation

```sh
su -
easy_install pip
pip install git+git://github.com/cluck/osxmkhomedir.git
```

