# -*- coding: utf-8 -*-

from __future__ import unicode_literals

__version__ = '3.5.0'
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
import logging
import logging.handlers

cmd = os.path.abspath(sys.argv[0])
base = os.path.basename(cmd)
if base not in ('osxmkhomedir', 'osxmkhomedir-hook') and __name__ != "__main__":
    raise RuntimeError('binary should be called osxmkhomedir, not ' + base)


def init_logging(logf):
    logger = logging.getLogger('')
    logger.setLevel(logging.DEBUG)
    if logf:
        l = logging.handlers.RotatingFileHandler(logf, maxBytes=0,
                                                 backupCount=8, encoding='utf-8')
        fl = logging.Formatter(u'%(asctime)s %(levelname)s: %(message)s')
        l.setFormatter(fl)
        l.setLevel(logging.DEBUG)
        l.doRollover()
        logger.addHandler(l)
    #
    cons = logging.StreamHandler()   # sys.stderr
    if logf:
        fc = logging.Formatter('[%(levelname)s](%(name)s): %(message)s')
    else:
        fc = logging.Formatter('%(message)s')
    cons.setFormatter(fc)
    cons.setLevel(logging.CRITICAL)
    logger.addHandler(cons)
    # osxmkhomedir convention:
    logger.console_handler = cons
    return logger


def log_communicate(p, log):
    eof = [False, False]
    readfh = [p.stdout.fileno(), p.stderr.fileno()]
    while True:
        selfh = select.select(readfh, [], [])
        for fd in selfh[0]:
            if not eof[0] and fd == readfh[0]:
                inout = p.stdout.readline()
                if len(inout) == 0:
                    eof[0] = True
                    continue
                inout = inout.decode('utf8', 'replace').rstrip()           
                if len(inout) != 0:
                    log.debug(inout)
            if not eof[1] and fd == readfh[1]:
                inerr = p.stderr.readline()
                if len(inerr) == 0:
                    eof[1] = True
                    continue
                inerr = inerr.decode('utf8', 'replace').rstrip()
                if len(inerr) != 0:
                    log.error(inerr)
        if p.poll() != None:
            if eof[0] == True and eof[1] == True:
                break
    p.communicate()
    if p.returncode:
        log.error('Command returned error code %d', p.returncode)
    return p.returncode


def install(log):
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
        log.info('Removed obsolete {0}'.format(plist_file))
    except OSError:
        pass
    child = subprocess.Popen(['defaults', 'write', 'com.apple.loginwindow',
        'LoginHook', '/usr/local/bin/osxmkhomedir-hook'],
        stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    log_communicate(child, log)

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
            log.warn('osxmkhomedir: /etc/sudoers busy, try again later')
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
            log.info('Already installed in /etc/sudoers')
            return
        with open('/etc/sudoers.tmp', 'w', fopts) as tmpf:        
            tmpf.write(sudoers)
        child = subprocess.Popen(['visudo', '-c', '-f', '/etc/sudoers.tmp'],
            stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        log_communicate(child, log)
        if not child.returncode:
            shutil.move('/etc/sudoers.tmp', '/etc/sudoers')
            os.chmod('/etc/sudoers', 0440)
            os.chown('/etc/sudoers', 0, 0)
            log.info('Written /etc/sudoers')
        else:
            log.error('Error building /etc/sudoers, not installed')
            os.unlink('/etc/sudoers.tmp')
            return 1


def usage(ret=0):
    print('{0}: {1}'.format(sys.argv[0], '[--install]'))
    return ret


def check_secure(login_script, log):
    isok = True
    if not os.path.exists(login_script):
        log.error('Does not exist: {0}'.format(login_script))
        return None
    if not os.path.isfile(login_script):
        log.error('Is not a regular file: {0}'.format(login_script))
        return False
    if not os.access(login_script, os.X_OK):
        log.error('Not executable: {0}'.format(login_script))
        isok = False
    login_script_stat = os.stat(login_script)
    if login_script_stat.st_uid:
        name = pwd.getpwuid(login_script_stat.st_uid).pw_name
        if (name not in grp.getgrnam('admin').gr_mem):
            log.error('Insecure script owner: {0}'.format(login_script))
            isok = False
    if grp.getgrgid(login_script_stat.st_gid).gr_name not in ('root', 'admin', 'wheel'):
        log.error('Insecure script group: {0}'.format(login_script))
        isok = False
    if (login_script_stat.st_mode & 0777) & ~0775:
        log.error('Insecure script permissions: {0}'.format(login_script))
        isok = False
    #
    login_dir = os.path.dirname(login_script)
    login_dir_stat = os.stat(login_dir)
    if login_dir_stat.st_uid:
        name = pwd.getpwuid(login_dir_stat.st_uid).pw_name
        if (name not in grp.getgrnam('admin').gr_mem):
            log.error('Insecure dir owner: {0}'.format(login_dir))
            isok = False
    if grp.getgrgid(login_dir_stat.st_gid).gr_name not in ('root', 'admin', 'wheel'):
        log.error('Insecure dir group: {0}'.format(login_dir))
        isok = False
    if (login_dir_stat.st_mode & 0777) & ~0775:
        log.error('Insecure dir permissions: {0}'.format(login_dir))
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
            log.error("{0}: {1} ({2})\n".format(type(e).__name__, str(e), r))
            raise SystemExit(1)
        scripts.setdefault(rn, ['upgrade{0:d}.sh'.format(rn), 'upgrade{0:d}-privileged.sh'.format(rn)])
        scripts[rn][int(r.endswith('-privileged.sh'))] = os.path.basename(r)
        if rn > max_:
            max_ = rn
    for rn in range(1, max_+1):
        if rn not in scripts:
            scripts[rn] = ['upgrade{0:d}.sh'.format(rn), 'upgrade{0:d}-privileged.sh'.format(rn)]
    return max_, scripts


def run(uid, args, log):

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
        if check_secure(cmd, log):
            for rev in range(userRevision+1, max_revision+1):
                upgrade_script = os.path.join('/usr/local/Library/osxmkhomedir', scripts[rev][0])
                if not args.no_root:
                    sudo_cmd = ['/usr/bin/sudo', '-n', cmd, '--run', '--uid', str(os.getuid()),
                        '--revision', scripts[rev][1], '--log', '>{0}'.format(log.level)]
                    child = subprocess.Popen(sudo_cmd, env=os.environ,
                        stderr=subprocess.PIPE, stdout=subprocess.PIPE)
                    log_communicate(child, log)
                    script_errors |= child.returncode
                #
                print(upgrade_script)
                if script_errors != 0:
                    log.debug(' Skipped: {0}'.format(upgrade_script))
                elif check_secure(upgrade_script, log):
                    script_cmd = [upgrade_script, pw_user.pw_name, pw_user.pw_dir]
                    child = subprocess.Popen(script_cmd, env=os.environ,
                        stderr=subprocess.PIPE, stdout=subprocess.PIPE)
                    log_communicate(child, log)
                    script_errors |= child.returncode
                if script_errors == 0:
                    updatedRevision = rev
                else:
                    log.error('Upgrade scripts failed due to errors ({0})'.format(script_errors))
                    conf['revision'] = updatedRevision
                    plistlib.writePlist(conf, conf_file)
                    return script_errors
            # root login
            if not args.no_root:
                sudo_cmd = ['/usr/bin/sudo', '-n', cmd, '--run', '--uid', str(os.getuid()),
                            '--login', '--log', '>{0}'.format(log.level)]
                child = subprocess.Popen(sudo_cmd, env=os.environ,
                    stderr=subprocess.PIPE, stdout=subprocess.PIPE)
                log_communicate(child, log)
                script_errors |= child.returncode
            if script_errors != 0:
                log.error('Login scripts failed due to errors ({0})'.format(script_errors))
                conf['revision'] = updatedRevision
                plistlib.writePlist(conf, conf_file)
                return script_errors
        #
        login_script = ['/usr/local/Library/osxmkhomedir/login.sh', pw_user.pw_name, pw_user.pw_dir]
        if check_secure(login_script[0], log):
            child = subprocess.Popen(login_script, env=os.environ,
                stderr=subprocess.PIPE, stdout=subprocess.PIPE)
            log_communicate(child, log)
            script_errors |= child.returncode
        #
        if script_errors == 0:
            conf['revision'] = updatedRevision
            plistlib.writePlist(conf, conf_file)
    elif not args.no_root:
        if uid is None:
            raise RuntimeError('Calling arguments error')
        pw_user = pwd.getpwuid(uid)
        #
        if args.revision and args.revision.endswith('-privileged.sh'):
            revision = os.path.basename(args.revision)
            upgrade_script = os.path.join('/usr/local/Library/osxmkhomedir', revision)
            safety_check = check_secure(upgrade_script, log)
            if safety_check:
                child = subprocess.Popen([upgrade_script, pw_user.pw_name, pw_user.pw_dir], env=os.environ,
                    stderr=subprocess.PIPE, stdout=subprocess.PIPE)
                log_communicate(child, log)
                script_errors |= child.returncode
            elif safety_check == False:
                script_errors |= 1
        #
        if script_errors == 0 and args.login == True:
            login_script = '/usr/local/Library/osxmkhomedir/login-privileged.sh'
            if check_secure(login_script, log):
                child = subprocess.Popen([login_script, pw_user.pw_name, pw_user.pw_dir], env=os.environ,
                    stderr=subprocess.PIPE, stdout=subprocess.PIPE)
                log_communicate(child, log)
                script_errors |= child.returncode
    else:
        log.info('Nothing to do')
    return script_errors


#def test(pid, debug=False):
#    cmd = ["/bin/launchctl", "bsexec", pid, "chroot", "-u", uid, "-g", gid, "/", "/bin/launchctl", "load", "-S", "Aqua", plist]
#    child = subprocess.Popen(cmd, env=os.environ,
#                    stderr=subprocess.PIPE, stdout=subprocess.PIPE)
#                log_communicate(child, verbose=debug)


def main(argv):
    import argparse

    default_log_file = os.path.expanduser('~/Library/Logs/osxmkhomedir.log')

    parser = argparse.ArgumentParser(description='osxmkhomedir')
    #
    parser.add_argument('-v', '--verbose', help='increment verbosity', action='count')
    parser.add_argument('-i', '--install', help='install %(prog)s', action='store_true')
    parser.add_argument('--update', help='update %(prog)s', action='store_true')
    #
    parser.add_argument('-u', '--uid', type=int)
    parser.add_argument('-r', '--revision')  # Note: string, not int
    parser.add_argument('--run', help='run scripts (for debugging only)', action='store_true')
    parser.add_argument('--login', help='login (internal command)', action='store_true')
    parser.add_argument('--log', default=default_log_file, help='log file')
    parser.add_argument('--no-root', help='skip privileged scripts (internal command)', action='store_true')
    #parser.add_argument('--test', help='test (use with extreme caution)', action='store_true')
    #
    args = parser.parse_args()

    if args.update:
        import pip
        return pip.main(['install', '--upgrade', 'https://github.com/cluck/osxmkhomedir/archive/master.tar.gz'])

    #if args.test:
    #    return test(debug=args.debug)
    
    if args.log.startswith('>'):
        log = init_logging(None)
        log.console_handler.setLevel(int(args.log[1:]))
    else:
        log = init_logging(args.log)
        if not args.verbose:
            log.console_handler.setLevel('ERROR')
        elif args.verbose == 1:
            log.console_handler.setLevel('WARNING')
        elif args.verbose == 2:
            log.console_handler.setLevel('INFO')
        elif args.verbose >= 3:
            log.console_handler.setLevel('DEBUG')
        
    if args.install:
        return install(log)

    if args.run:
        ret = run(args.uid, args, log)
        if ret:
            log.debug('Exiting with error %s', ret) 
        return ret

    print('osxmkhomedir {0}, Copyright (C) 2015, {1}'.format(__version__, __author__))
    parser.print_usage()
    return 1


def login_hook():
    """
    This is for com.apple.loginwindow LoginHook, to be installed by:
    
        defaults write com.apple.loginwindow LoginHook /path/to/script
    
    OS X will call this script as root, and the user logging in is passed in sys.argv[1].
    Default locale will be set to "C", PATH to a minimal subset and the cwd to /.
    """
    os.environ['PATH'] = '/usr/local/sbin:/usr/local/bin:' + os.environ.get('PATH', '')
    os.environ['LC_CTYPE'] = 'UTF-8'
    try:
        user = sys.argv[1]
        uid = pwd.getpwnam(user).pw_uid
    except:
        print('Usage: osxmkhomedir-hook <username>')
        sys.exit(1)
    login_script = '/usr/local/bin/osxmkhomedir'
    #if check_secure(login_script, log):
    child = subprocess.Popen(['/usr/bin/sudo', '-n', '-u', user, login_script,
        '--run', '--no-root'], env={},
        stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    log_communicate(child, log)


def command():
   sys.exit(main(sys.argv[1:]))

if __name__ == "__main__":
   sys.exit(main(sys.argv[1:]))

