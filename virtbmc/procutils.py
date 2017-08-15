#!/usr/bin/env python

import shlex
import subprocess
import logging
import os
import fcntl
import select
import time


class InteractiveProcess(object):

    def __init__(self, cmds, **kwargs):
        timeout = kwargs.pop('timeout', -1)
        if timeout > 0:
            cmds = ['timeout', '--signal=KILL', '%ds' % timeout] + cmds
        self.cmds = map(str, cmds)
        self.disassociate = kwargs.pop('disassociate', False)
        self.redirect_file = kwargs.pop('redirect_file', None)
        self.is_redirect = False

    def start(self):
        kwargs = {
            'stdin': subprocess.PIPE,
            'stdout': subprocess.PIPE,
            'stderr': subprocess.STDOUT,
            'close_fds': True,
        }
        if self.redirect_file is not None:
            if not hasattr(self.redirect_file, 'write'):
                raise Exception('%s is not a opening file for IO redirect' % self.redirect_file)
            else:
                self.is_redirect = True
                kwargs['stdout'] = self.redirect_file
                kwargs['stderr'] = subprocess.PIPE
        if self.disassociate:
            kwargs['preexec_fn'] = os.setsid
        self.proc = subprocess.Popen(self.cmds, **kwargs)

    def get_output_no_exception(self):
        lines = ''
        fd = self.proc.stdout if not self.is_redirect else self.proc.stderr
        fdno = fd.fileno()
        fl = fcntl.fcntl(fdno, fcntl.F_GETFL)
        fcntl.fcntl(fdno, fcntl.F_SETFL, fl | os.O_NONBLOCK)
        is_exit = False
        while not is_exit:
            try:
                r, w, x = select.select([fdno], [], [fdno], 1)
                if fdno in r:
                    lines += fd.read()
                elif fdno in x:
                    break
            except:
                pass
            is_exit = self.proc.poll() is not None
        try:
            extra = fd.read()
            while extra:
                lines += extra
                time.sleep(0.001)
                try:
                    extra = fd.read()
                except:
                    pass
        except:
            pass
        ret = map(str.strip, lines.split('\n'))
        return ret

    def get_output(self):
        ret = self.get_output_no_exception()
        self.returncode = self.proc.poll()
        if self.returncode > 0:
            raise Exception('\n'.join(ret))
        return ret

    def send(self, cmd):
        self.proc.stdin.write('%s\n' % cmd)

    def is_exit(self):
        time.sleep(0.1)
        self.proc.poll()
        if self.proc.returncode is None:
            return False
        else:
            self.returncode = self.proc.returncode
            return True

    def get_returncode(self):
        return self.returncode

    def kill(self):
        self.proc.kill()
        return self.is_exit()


def check_call(cmds, **kwargs):
    timeout = kwargs.pop('timeout', -1)
    if timeout > 0:
        cmds = ['timeout', '--signal=KILL', '%ds' % timeout] + cmds
    cmds = map(str, cmds)
    params = {'close_fds': True}
    if kwargs.get('disassociate', False):
        params['preexec_fn'] = os.setsid
    return subprocess.check_call(cmds, **params)


def check_call_no_exception(cmds, **kwargs):
    try:
        if check_call(cmds, **kwargs) == 0:
            return True
    except Exception as e:
        logging.warning(e)
    return False


def check_output(cmds, **kwargs):
    if isinstance(cmds, basestring):
        cmds = shlex.split(cmds)
    elif not hasattr(cmds, '__iter__'):
        raise Exception('Invalid type of commands: %s' % cmds)
    proc = InteractiveProcess(cmds, **kwargs)
    proc.start()
    if kwargs.get('ignore_exception', False):
        return proc.get_output_no_exception()
    return proc.get_output()


def check_output_no_exception(cmds, **kwargs):
    try:
        return check_output(cmds, **kwargs)
    except Exception as e:
        logging.warning('check_output error: %s', str(e))
        return None


def check_pid_alive(pidfile, progname):
    with open(pidfile, 'r') as f:
        pid = f.read()
    procpath = '/proc/%s/cmdline' % pid.strip()
    if os.path.isfile(procpath):
        with open(procpath, 'r') as f:
            cmdline = f.read()
        return progname in cmdline
    return False


if __name__ == '__main__':

    # normal
    print check_output('ls')
    print check_output(['ls', '-a'])

    with open('test_io_redirect1', 'w') as f:
        print check_output('ls -ls', redirect_file=f)

    # exception:
    try:
        print check_output('ls a_not_exsisting_file')
    except Exception as e:
        print e
