#! -*- coding: utf-8 -*-

from __future__ import unicode_literals

__version__ = '2.4.0'
__author__ = 'Claudio Luck'
__author_email__ = 'claudio.luck@gmail.com'

import sys
import os
import codecs
import getopt
import glob
import grp
import plistlib
import pwd
import shutil
import subprocess

cmd = os.path.abspath(sys.argv[0])
base = os.path.basename(cmd)
if base not in ('osxmkhomedir', 'osxmkhomedir-hook') and __name__ != "__main__":
    raise RuntimeError('binary should be called osxmkhomedir, not ' + base)


def install():
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
    child.communicate()

    # Check/edit /etc/sudoers
    lines = (
        '\nALL ALL=(ALL) NOPASSWD: {cmd:s} --run\n'.format(cmd=cmd),
        # lines to be replaced with the above:
        '\nALL ALL=(root) NOPASSWD: {cmd:s} --run\n'.format(cmd=cmd),
    )
    with open('/etc/sudoers.tmp', 'w', os.O_EXCL) as tmpf:
        with codecs.open('/etc/sudoers', 'r') as origf:
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
            tmpf.write(sudoers)
        child = subprocess.Popen(['visudo', '-c', '-f', '/etc/sudoers.tmp'],
            stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        visudo = child.communicate()
        if not child.returncode:
            shutil.move('/etc/sudoers.tmp', '/etc/sudoers')
            os.chmod('/etc/sudoers', 0440)
            os.chown('/etc/sudoers', 0, 0)
            print('Written /etc/sudoers')
        else:
            print(sudoers)
            print(''.join(visudo))
            print('ERROR writing /etc/sudoers')
            return 1


def usage(ret=0):
    print('{0}: {1}'.format(sys.argv[0], '[--install]'))
    return ret


def check_secure(login_script):
    isok = True
    if not os.path.isfile(login_script):
        print('Does not exist: {0}'.format(login_script))
        return False
    if not os.access(login_script, os.X_OK):
        print('Not executable: {0}'.format(login_script))
        isok = False
    login_script_stat = os.stat(login_script)
    if login_script_stat.st_uid:
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
    max = 1
    rn = 0
    scripts = dict()
    revs = glob.iglob('/usr/local/Library/osxmkhomedir/upgrade[0-9]*.sh')
    for r in revs:
        try:
            rn = int(os.path.splitext(os.path.basename(r))[0].split('-', 1)[0][7:])
        except ValueError as e:
            print("{0}: {1} ({2})".format(type(e).__name__, str(e), r))
        scripts.setdefault(rn, ['upgrade{0:d}.sh'.format(rn), 'upgrade{0:d}-privileged.sh'.format(rn)])
        scripts[rn][int(r.endswith('-privileged.sh'))] = os.path.basename(r)
        if rn > max:
            max = rn
    for rn in range(1, max+1):
        if rn not in scripts:
            scripts[rn] = ['upgrade{0:d}.sh'.format(rn), 'upgrade{0:d}-privileged.sh'.format(rn)]
    return max, scripts


def run(uid, revision, login):

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
                    stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
                print(child.communicate()[0].rstrip('\n'))
                script_errors |= child.returncode
                #
                if script_errors != 0:
                    print(' Skipped: {0}'.format(upgrade_script))
                elif check_secure(upgrade_script):
                    child = subprocess.Popen([upgrade_script, pw_user.pw_name, pw_user.pw_dir], env=os.environ,
                        stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
                    print(child.communicate()[0].rstrip('\n'))
                    script_errors |= child.returncode
                if script_errors == 0:
                    updatedRevision = rev
                else:
                    print(' Interruping due to error')
                    conf['revision'] = updatedRevision
                    plistlib.writePlist(conf, conf_file)
                    return script_errors
            # root login
            sudo_cmd = ['/usr/bin/sudo', '-n', cmd, '--run', '--uid', str(os.getuid()), '--login']
            child = subprocess.Popen(sudo_cmd, env=os.environ,
                stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
            print(child.communicate()[0].rstrip('\n'))
            script_errors |= child.returncode
            if script_errors != 0:
                print(' Interruping due to error')
                conf['revision'] = updatedRevision
                plistlib.writePlist(conf, conf_file)
                return script_errors
        #
        login_script = '/usr/local/Library/osxmkhomedir/login.sh'
        if check_secure(login_script):
            child = subprocess.Popen([login_script, pw_user.pw_name, pw_user.pw_dir], env=os.environ,
                stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
            print(child.communicate()[0].rstrip('\n'))
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
            upgrade_script = os.path.join('/usr/local/Library/osxmkhomedir', revision)
            if check_secure(upgrade_script):
                child = subprocess.Popen([upgrade_script, pw_user.pw_name, pw_user.pw_dir], env=os.environ,
                    stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
                print(child.communicate()[0].rstrip('\n'))
                script_errors |= child.returncode
        #
        if script_errors == 0 and login == True:
            login_script = '/usr/local/Library/osxmkhomedir/login-privileged.sh'
            if check_secure(login_script):
                child = subprocess.Popen([login_script, pw_user.pw_name, pw_user.pw_dir], env=os.environ,
                    stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
                print(child.communicate()[0].rstrip('\n'))
                script_errors |= child.returncode
    return script_errors


def main(argv):
    try:
        opts, args = getopt.getopt(argv, "hiu:r:", ["help", "install", "run", "uid=", "revision=", "login"])
    except getopt.GetoptError as e:
        return usage(2)
    uid = None
    revision = None
    login = False
    for opt, arg in opts:
        if opt in ('-u', '--uid'):
            uid = int(arg)
        elif opt in ('-r', '--revision'):
            revision = arg
        elif opt in ('--login'):
            login = True
    for opt, arg in opts:
        if opt in ('-h', '--help'):
            return usage()
        elif opt in ('-i', '--install'):
            return install()
        elif opt in ('-r', '--run'):
            return run(uid=uid, revision=revision, login=login)
    return usage(1)


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
            env={}, stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
        print(child.communicate()[0].rstrip('\n'))


def command():
   sys.exit(main(sys.argv[1:]))

if __name__ == "__main__":
   sys.exit(main(sys.argv[1:]))

