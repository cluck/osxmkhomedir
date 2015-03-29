# OS X mkhomedir help scripts

This is a command line utility for OS X that installs itself as a launch agent
when an user proceeds to login.

Through granting itself password-less sudo rights and storing a preference file in the
users home, it allows for the Admin to run commands to finalize and maintain users profiles,
either as root or the logging in user, and either on the first login or every time.

* /usr/local/Library/osxmkhomedir
** login-privileged-first.sh - runs as user root when the user logs in for the first time
** login-privileged.sh - runs as user root when the user logs in, also on the first time
** login-first.sh - runs as the logging in user when the user logs in for the first time
** login.sh - runs as the logging in user, also on the first time

