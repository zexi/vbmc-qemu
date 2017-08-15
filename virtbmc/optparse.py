#!/usr/bin/env python

import sys
import os
import argparse

import virtbmc.utils as utils
from virtbmc.version import version
from virtbmc import models
from virtbmc import manager


def init_argparser():
    parser = argparse.ArgumentParser(
        prog='qemu-vbmc',
        description='%(prog)s Qemu virtual BMC simulation tool',
    )
    parser.add_argument("-v", "--version", help="Show version",
                        action='version', version='%(prog)s'+' %s' % version())

    subparsers = parser.add_subparsers(help='commands')

    # Options shared by all subparsers
    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument("-d", "--verbose", help="increase output verbosity",
                        action="store_true")

    # Database
    db_parser = subparsers.add_parser(
        'db', parents=[parent_parser],
        help='Database management',
    )
    db_parser.add_argument('--init', action='store_true', help='Init sqlite database')
    db_parser.add_argument('--remove', action='store_true', help='Remove sqlite database')
    db_parser.set_defaults(func=models.manage)

    # Create
    create_parser = subparsers.add_parser(
        'create', parents=[parent_parser],
        help='Create VMs with BMC',
    )
    create_parser.add_argument("-n", "--number", type=int, default=0,
                        help="start virtual qemu bmc of a given number")
    create_parser.add_argument("--image-size", type=str, dest='image_size',
                        default='20G', help="specified image size used by qemu/kvm")
    create_parser.add_argument("-b", "--bridge", type=str, default='br0',
                        help="bridge interface name")
    create_parser.add_argument("--qemu", type=str, default='/opt/qemu2.7/bin/qemu-system-x86_64',
                        help="qemu binary execute path")
    create_parser.add_argument("--ipmi-sim", type=str, dest="ipmi_sim",
                        default='/opt/openipmi/bin/ipmi_sim', help="ipmi-sim binary execute path")
    create_parser.add_argument("--memory", type=int, default=4096,
                        help="qemu VM memory size")
    create_parser.add_argument("--ncpu", type=int, default=1,
                        help="qemu VM cpu number")
    create_parser.add_argument("--template", type=str, default=utils.dirname(__file__, 1)+os.sep+'templates',
                        help="template scripts dirpath")
    create_parser.set_defaults(func=manager.create)

    # Start
    start_parser = subparsers.add_parser(
        'start', parents=[parent_parser],
        help='Start VMs with BMC',
    )
    start_parser.add_argument("bmc", nargs='+',
                        help="start BMC, default start all")
    start_parser.add_argument("--vm", dest='autostart_vm',
                        help="autostart qemu vm when BMC run",
                        action="store_true")
    start_parser.set_defaults(func=manager.start)

    # List
    list_parser = subparsers.add_parser(
        'list', parents=[parent_parser],
        help='List VMs',
    )
    list_parser.add_argument("--json", help="json output",
                        action="store_true")
    list_parser.set_defaults(func=manager.list_all)

    # Update
    update_parser = subparsers.add_parser(
        'update', parents=[parent_parser],
        help='Update VMs',
    )
    update_parser.add_argument('id', nargs='+',
                               help='Update specify BMCs')
    update_parser.add_argument("-u", "--ipmi-user", help="ipmi user")
    update_parser.add_argument("-p", "--ipmi-password", help="ipmi password")
    update_parser.add_argument("--json", help="json output",
                        action="store_true")
    update_parser.set_defaults(func=manager.update)

    # Delete
    delete_parser = subparsers.add_parser(
        'delete', parents=[parent_parser],
        help='Delete Vm',
    )
    delete_parser.add_argument('id', nargs='+',
                               help='Delete specify BMCs')
    delete_parser.set_defaults(func=manager.delete)

    # Stop
    stop_parser = subparsers.add_parser(
        'stop', parents=[parent_parser],
        help='Stop BMCs & Vms',
    )
    stop_parser.add_argument("id", nargs='+',
                        help="stop specify BMCs & Vms")
    stop_parser.set_defaults(func=manager.stop)

    return parser


def check_args(parser):

    def error_exit(msg):
        parser.print_help()
        sys.exit(msg)

    args = parser.parse_args()
    return parser, args


_opt_parser = None
_args = None


def get_parser():
    return _opt_parser


def get_args():
    return _args


def init():
    global _opt_parser
    global _args
    if not _opt_parser or not _args:
        _opt_parser, _args = check_args(init_argparser())
