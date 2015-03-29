#! -*- coding: utf-8 -*-

__version__ = '1.1.0'
__author__ = 'Claudio Luck'
__author_email__ = 'claudio.luck@gmail.com'

import sys
import os
import getopt
import codecs
import subprocess
import shutil
import grp
import pwd

cmd = os.path.abspath(sys.argv[0])
base = os.path.basename(cmd)
if base != 'osxmkhomedir' and __name__ != "__main__":
    raise RuntimeError('binary should be called osxmkhomedir, not ' + base)


def install():
    template = """\
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Disabled</key>
    <false/>
    <key>Label</key>
    <string>OS X mkhomedir</string>
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
    with codecs.open(plist_file, 'w', 'utf-8') as plist:
        plist.write(template.format(cmd=cmd, base=base))
    os.chmod(plist_file, 0644)
    os.chown(plist_file, 0, 0) 
    print('Written {0}'.format(plist_file))

    # Check/edit /etc/sudoers
    line = '\nALL ALL=(root) NOPASSWD: {cmd:s} --run\n'.format(cmd=cmd)
    with open('/etc/sudoers.tmp', 'w', os.O_EXCL) as tmpf:
        with codecs.open('/etc/sudoers', 'r') as origf:
            sudoers = origf.read()
            if line in sudoers:
                print('Already installed /etc/sudoers')
                return
            tmpf.write(sudoers)
        tmpf.write(line + '\n')
        child = subprocess.Popen(['visudo', '-c', '-f', '/etc/sudoers.tmp'],
            stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        child.communicate()
        if not child.returncode:
            shutil.move('/etc/sudoers.tmp', '/etc/sudoers')
            os.chmod('/etc/sudoers', 0440)
            os.chown('/etc/sudoers', 0, 0)
        print('Written /etc/sudoers')


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
    if grp.getgrgid(login_script_stat.st_gid).gr_name not in ('root', 'admin'):
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
    if grp.getgrgid(login_dir_stat.st_gid).gr_name not in ('root', 'admin'):
        print('Insecure dir group: {0}'.format(login_dir))
        isok = False
    if (login_dir_stat.st_mode & 0777) & ~0775:
        print('Insecure dir permissions: {0}'.format(login_dir))
        isok = False
    return isok


def run(uid=None, firstRun=True):
    if 'SUDO_ASKPASS' in os.environ:
        del os.environ['SUDO_ASKPASS'] 

    if os.getuid() != 0:
        import plistlib
        conf_file = os.path.expanduser('~/Library/Preferences/ch.cluck.osxmkhomedir.plist')
        try:
            conf = plistlib.readPlist(conf_file)
        except IOError:
            conf = dict(firstRun=True)
        conf['firstRun'] |= firstRun
        pw_user = pwd.getpwuid(os.getuid())
        #
        if check_secure(cmd):
            env=os.environ.copy()
            sudo_cmd = ['/usr/bin/sudo', cmd, '--run', '--uid', str(os.getuid())]
            if conf['firstRun']:
                sudo_cmd.append('--first')
            child = subprocess.Popen(sudo_cmd, env=os.environ,
                stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
            print(child.communicate()[0].rstrip('\n'))
        else:
            print(' Skipped: {0}'.format(cmd))
        #
        if conf['firstRun']:
            login_script = '/usr/local/Library/osxmkhomedir/login-first.sh'
            if check_secure(login_script):
                child = subprocess.Popen([login_script, pw_user.pw_name, pw_user.pw_dir], env=os.environ,
                    stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
                print(child.communicate()[0].rstrip('\n'))
            else:
                print(' Skipped: {0}'.format(login_script))
        #
        login_script = '/usr/local/Library/osxmkhomedir/login.sh'
        if check_secure(login_script):
            check_secure(login_script)
            child = subprocess.Popen([login_script, pw_user.pw_name, pw_user.pw_dir], env=os.environ,
                stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
            print(child.communicate()[0].rstrip('\n'))
        else:
            print(' Skipped: {0}'.format(login_script))
        #
        conf['firstRun'] = False
        plistlib.writePlist(conf, conf_file)
    else:
        if uid is None:
            raise RuntimeError('Missing: --uid=<uid>')
        pw_user = pwd.getpwuid(uid)
        #
        if firstRun:
            login_script = '/usr/local/Library/osxmkhomedir/login-privileged-first.sh'
            if check_secure(login_script):
                child = subprocess.Popen([login_script, pw_user.pw_name, pw_user.pw_dir], env=os.environ,
                    stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
                print(child.communicate()[0].rstrip('\n'))
            else:
                print(' Skipped: {0}'.format(login_script))
        #
        login_script = '/usr/local/Library/osxmkhomedir/login-privileged.sh'
        if check_secure(login_script):
            check_secure(login_script)
            child = subprocess.Popen([login_script, pw_user.pw_name, pw_user.pw_dir], env=os.environ,
                stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
            print(child.communicate()[0].rstrip('\n'))
        else:
            print(' Skipped: {0}'.format(login_script))


def main(argv):
    try:
        opts, args = getopt.getopt(argv, "", ["install", "run", "uid=", "first"])
    except getopt.GetoptError:
        return usage(2)
    uid = None
    firstRun = False
    for opt, arg in opts:
        if opt in ('--uid'):
            uid = int(arg)
        if opt in ('--first'):
            firstRun = True
    for opt, arg in opts:
        if opt in ('-h', '--help'):
            return usage()
        elif opt in ('-i', '--install'):
            return install()
        elif opt in ('-r', '--run'):
            return run(uid=uid, firstRun=firstRun)
    return usage(1)


def command():
   sys.exit(main(sys.argv[1:]))

if __name__ == "__main__":
   sys.exit(main(sys.argv[1:]))

