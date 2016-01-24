# -*- coding: utf-8 -*-

from __future__ import unicode_literals

__version__ = '3.3.0'
__author__ = 'Claudio Luck'
__author_email__ = 'claudio.luck@gmail.com'

import sys
import os
import fcntl
import getopt
import glob
import grp
import plistlib
import pwd
import select
import shutil
import subprocess

cmd = os.path.abspath(sys.argv[0])
base = os.path.basename(cmd)
if base not in ('osxmkhomedir', 'osxmkhomedir-hook') and __name__ != "__main__":
    raise RuntimeError('binary should be called osxmkhomedir, not ' + base)


def print_communicate(p, buffer=False, verbose=True):

    stdout = []
    stderr = []

    while True:
        readfh = [p.stdout.fileno(), p.stderr.fileno()]
        selfh = select.select(readfh, [], [])

        for fd in selfh[0]:
            if fd == p.stdout.fileno():
                indata = p.stdout.readline()
                if verbose:
                    sys.stdout.write(indata)
                if buffer:
                    stdout.append(indata)
            if fd == p.stderr.fileno():
                indata = p.stderr.readline()
                sys.stderr.write(indata)
                if buffer:
                    stderr.append(indata)

        if p.poll() != None:
            break

    stdout = ''.join(stdout)
    stderr = ''.join(stderr)

    return stdout, stderr



def install(debug=False):
    template = u"""\
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Disabled</key>
    <false/>
    <key>Label</key>
    <string>osxmkhomedir</string>
    <key>Program</key>
    <string>{cmd:s}</string>
    <key>ProgramArguments</key>
    <array>
        <string>--run</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
    <key>StandardErrorPath</key>
    <string>/var/log/{base:s}.err</string>
    <key>StandardOutPath</key>
    <string>/var/log/{base:s}.out</string>
</dict>
</plist>
"""
    plist_file = '/Library/LaunchAgents/{base:s}.plist'.format(base=base)
    #with codecs.open(plist_file, 'w', 'utf-8') as plist:
    #    plist.write(template.format(cmd=cmd, base=base))
    #os.chmod(plist_file, 0644)
    #os.chown(plist_file, 0, 0) 
    #print('Written {0}'.format(plist_file))
    #child = subprocess.Popen(['launchctl', 'unload', 'osxmkhomedir'],
    #    stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    #child.communicate()
    try:
        os.unlink(plist_file)
        print('Removed obsolete {0}'.format(plist_file))
    except OSError:
        pass
    child = subprocess.Popen(['defaults', 'write', 'com.apple.loginwindow',
        'LoginHook', '/usr/local/bin/osxmkhomedir-hook'],
        stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    print_communicate(child, verbose=debug)

    # Check/edit /etc/sudoers
    lines = (
        '\nALL ALL=(ALL) NOPASSWD: {cmd:s} --run*\n'.format(cmd=cmd),
        # lines to be replaced with the above:
        '\nALL ALL=(ALL) NOPASSWD: {cmd:s} --run\n'.format(cmd=cmd),
        '\nALL ALL=(root) NOPASSWD: {cmd:s} --run\n'.format(cmd=cmd),
    )
    fopts = os.O_EXCL | getattr(os, 'O_EXLOCK', 0)
    with open('/etc/sudoers', 'r', os.O_RDWR | fopts) as origf:
        try:
            fcntl.flock(origf, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except IOError:
            print('osxmkhomedir: /etc/sudoers busy, try again later')
            return 1
        sudoers0 = sudoers = origf.read()
        for line in lines[1:]:
           if lines[0] not in sudoers:
               sudoers = sudoers.replace(line, lines[0])
           else:
               sudoers = sudoers.replace(line, '\n# ' + line.lstrip('\n'))
        if lines[0] not in sudoers:
            sudoers += lines[0] + '\n'
        if sudoers == sudoers0:
            print('Already installed in /etc/sudoers')
            return
        with open('/etc/sudoers.tmp', 'w', fopts) as tmpf:        
            tmpf.write(sudoers)
        child = subprocess.Popen(['visudo', '-c', '-f', '/etc/sudoers.tmp'],
            stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        print_communicate(child, verbose=debug)
        if not child.returncode:
            shutil.move('/etc/sudoers.tmp', '/etc/sudoers')
            os.chmod('/etc/sudoers', 0440)
            os.chown('/etc/sudoers', 0, 0)
            print('Written /etc/sudoers')
        else:
            print('Error building /etc/sudoers, not installed')
            os.unlink('/etc/sudoers.tmp')
            return 1


def usage(ret=0):
    print('{0}: {1}'.format(sys.argv[0], '[--install]'))
    return ret


def check_secure(login_script):
    isok = True
    if not os.path.exists(login_script):
        print('Does not exist: {0}'.format(login_script))
        return None
    if not os.path.isfile(login_script):
        print('Is not a regular file: {0}'.format(login_script))
        return False
    if not os.access(login_script, os.X_OK):
        print('Not executable: {0}'.format(login_script))
        isok = False
    login_script_stat = os.stat(login_script)
    if login_script_stat.st_uid:
        name = pwd.getpwuid(login_script_stat.st_uid).pw_name
        if (name not in grp.getgrnam('admin').gr_mem):
            print('Insecure script owner: {0}'.format(login_script))
            isok = False
    if grp.getgrgid(login_script_stat.st_gid).gr_name not in ('root', 'admin', 'wheel'):
        print('Insecure script group: {0}'.format(login_script))
        isok = False
    if (login_script_stat.st_mode & 0777) & ~0775:
        print('Insecure script permissions: {0}'.format(login_script))
        isok = False
    #
    login_dir = os.path.dirname(login_script)
    login_dir_stat = os.stat(login_dir)
    if login_dir_stat.st_uid:
        name = pwd.getpwuid(login_dir_stat.st_uid).pw_name
        if (name not in grp.getgrnam('admin').gr_mem):
            print('Insecure dir owner: {0}'.format(login_dir))
            isok = False
    if grp.getgrgid(login_dir_stat.st_gid).gr_name not in ('root', 'admin', 'wheel'):
        print('Insecure dir group: {0}'.format(login_dir))
        isok = False
    if (login_dir_stat.st_mode & 0777) & ~0775:
        print('Insecure dir permissions: {0}'.format(login_dir))
        isok = False
    return isok


def get_revisions():
    max_ = 1
    rn = 0
    scripts = dict()
    revs = glob.iglob('/usr/local/Library/osxmkhomedir/upgrade[0-9]*.sh')
    for r in revs:
        try:
            rn = int(os.path.splitext(os.path.basename(r))[0].split('-', 1)[0][7:])
        except ValueError as e:
            sys.stderr.write("{0}: {1} ({2})\n".format(type(e).__name__, str(e), r))
            raise SystemExit(1)
        scripts.setdefault(rn, ['upgrade{0:d}.sh'.format(rn), 'upgrade{0:d}-privileged.sh'.format(rn)])
        scripts[rn][int(r.endswith('-privileged.sh'))] = os.path.basename(r)
        if rn > max_:
            max_ = rn
    for rn in range(1, max_+1):
        if rn not in scripts:
            scripts[rn] = ['upgrade{0:d}.sh'.format(rn), 'upgrade{0:d}-privileged.sh'.format(rn)]
    return max_, scripts


def run(uid, revision, login, debug=False):

    if 'SUDO_ASKPASS' in os.environ:
        del os.environ['SUDO_ASKPASS'] 

    script_errors = 0

    if os.getuid() != 0:
        conf_file = os.path.expanduser('~/Library/Preferences/ch.cluck.osxmkhomedir.plist')
        try:
            conf = plistlib.readPlist(conf_file)
        except IOError:
            conf = dict(revision=0)
        userRevision = int(conf.get('revision', 0))
        updatedRevision = userRevision
        pw_user = pwd.getpwuid(os.getuid())
        max_revision, scripts = get_revisions()
        #
        if check_secure(cmd):
            for rev in range(userRevision+1, max_revision+1):
                upgrade_script = os.path.join('/usr/local/Library/osxmkhomedir', scripts[rev][0])
                sudo_cmd = ['/usr/bin/sudo', '-n', cmd, '--run', '--uid', str(os.getuid()),
                    '--revision', scripts[rev][1]]
                child = subprocess.Popen(sudo_cmd, env=os.environ,
                    stderr=subprocess.PIPE, stdout=subprocess.PIPE)
                print_communicate(child, verbose=debug)
                script_errors |= child.returncode
                #
                if script_errors != 0:
                    print(' Skipped: {0}'.format(upgrade_script))
                elif check_secure(upgrade_script):
                    child = subprocess.Popen([upgrade_script, pw_user.pw_name, pw_user.pw_dir], env=os.environ,
                        stderr=subprocess.PIPE, stdout=subprocess.PIPE)
                    print_communicate(child, verbose=debug)
                    script_errors |= child.returncode
                if script_errors == 0:
                    updatedRevision = rev
                else:
                    print('Upgrade scripts failed due to errors ({0})'.format(script_errors))
                    conf['revision'] = updatedRevision
                    plistlib.writePlist(conf, conf_file)
                    return script_errors
            # root login
            sudo_cmd = ['/usr/bin/sudo', '-n', cmd, '--run', '--uid', str(os.getuid()), '--login']
            child = subprocess.Popen(sudo_cmd, env=os.environ,
                stderr=subprocess.PIPE, stdout=subprocess.PIPE)
            print_communicate(child, verbose=debug)
            script_errors |= child.returncode
            if script_errors != 0:
                print('Login scripts failed due to errors ({0})'.format(script_errors))
                conf['revision'] = updatedRevision
                plistlib.writePlist(conf, conf_file)
                return script_errors
        #
        login_script = '/usr/local/Library/osxmkhomedir/login.sh'
        if check_secure(login_script):
            child = subprocess.Popen([login_script, pw_user.pw_name, pw_user.pw_dir], env=os.environ,
                stderr=subprocess.PIPE, stdout=subprocess.PIPE)
            print_communicate(child, verbose=debug)
            script_errors |= child.returncode
        #
        if script_errors == 0:
            conf['revision'] = updatedRevision
            plistlib.writePlist(conf, conf_file)
    else:
        if uid is None:
            raise RuntimeError('Calling arguments error')
        pw_user = pwd.getpwuid(uid)
        #
        if revision and revision.endswith('-privileged.sh'):
            revision = os.path.basename(revision)
            upgrade_script = os.path.join('/usr/local/Library/osxmkhomedir', revision)
            safety_check = check_secure(upgrade_script)
            if safety_check:
                child = subprocess.Popen([upgrade_script, pw_user.pw_name, pw_user.pw_dir], env=os.environ,
                    stderr=subprocess.PIPE, stdout=subprocess.PIPE)
                print_communicate(child, verbose=debug)
                script_errors |= child.returncode
            elif safety_check == False:
                script_errors |= 1
        #
        if script_errors == 0 and login == True:
            login_script = '/usr/local/Library/osxmkhomedir/login-privileged.sh'
            if check_secure(login_script):
                child = subprocess.Popen([login_script, pw_user.pw_name, pw_user.pw_dir], env=os.environ,
                    stderr=subprocess.PIPE, stdout=subprocess.PIPE)
                print_communicate(child, verbose=debug)
                script_errors |= child.returncode
    return script_errors


def main(argv):
    import argparse

    parser = argparse.ArgumentParser(description='osxmkhomedir')
    #
    parser.add_argument('-d', '--debug', help='enable debug output', action='store_true')
    parser.add_argument('-i', '--install', help='install %(prog)s', action='store_true')
    parser.add_argument('--update', help='update %(prog)s', action='store_true')
    #
    parser.add_argument('-u', '--uid', type=int)
    parser.add_argument('-r', '--revision', type=int)
    parser.add_argument('--run', help='run scripts (for debugging only)', action='store_true')
    parser.add_argument('--login', help='login (use with extreme caution)', action='store_true')
    #
    args = parser.parse_args()

    if args.update:
        import pip
        return pip.main(['install', '--upgrade', 'https://github.com/cluck/osxmkhomedir/archive/master.tar.gz'])

    if args.install:
        return install(debug=args.debug)

    if args.run:
        return run(uid=args.uid, revision=args.revision, login=args.login, debug=args.debug)

    parser.print_usage()
    return 1


def login_hook():
    # called as root, only argument should be the username for which it is running
    try:
        user = sys.argv[1]
        uid = pwd.getpwnam(user).pw_uid
    except:
        print('Usage: osmkhomedir-hook <username>')
        sys.exit(1)
    login_script = '/usr/local/bin/osxmkhomedir'
    if check_secure(login_script):
        # os.seteuid(uid)
        child = subprocess.Popen(['/usr/bin/sudo', '-n', '-u', user, login_script, '--run'],
            env={}, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        print_communicate(child, verbose=True)


def command():
   sys.exit(main(sys.argv[1:]))

if __name__ == "__main__":
   sys.exit(main(sys.argv[1:]))

