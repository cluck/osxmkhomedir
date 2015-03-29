# OS X mkhomedir help scripts

This is a command line utility for OS X that installs itself as a launch agent
on OS X, so that it is called when users log in.

Through granting itself password-less sudo rights and storing a preference file in the
users home, it allows for calling additional scripts to act upon user's home directory.

Additional scripts must be in the /usr/local/Library/osxmkhomedir directory, and both
directory and scripts must be owned by root:admin and not writable to other users.

* /usr/local/Library/osxmkhomedir
  * login-privileged-first.sh - runs as user root when the user logs in for the first time
  * login-privileged.sh - runs as user root when the user logs in, every time, also on the first time
  * login-first.sh - runs as the logging in user when the user logs in for the first time
  * login.sh - runs as the logging in user, every time, also on the first time

The additional scripts are called with the user's environment, and the username and
the home directory as arguments.

## Installation

```sh
su -
easy_install pip
pip install git+git://github.com/cluck/osxmkhomedir.git
```

