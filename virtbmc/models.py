#!/usr/bin/env python

import datetime

from peewee import *

import virtbmc.utils as utils
from virtbmc.config import DB_FILE


DB=None


def db_init():
    global DB
    if DB_FILE is None or len(DB_FILE) == 0:
        raise Exception("Database file is invaild: %s" % DB_FILE)
    utils.mkdir_of_file(DB_FILE)
    DB = SqliteDatabase(DB_FILE)
    return DB


class BaseModel(Model):
    class Meta:
        database = db_init()


class QemuVM(BaseModel):
    qemuname = TextField(unique=True)
    memory = IntegerField()
    ncpu = IntegerField()
    image_size = TextField()
    disk = TextField()
    ifup_script = TextField()
    ifdown_script = TextField()
    qemu_pidfile = TextField()
    controller_script = TextField()
    ifmac = TextField()
    vncport = IntegerField()
    uuid = TextField()
    created_date = DateTimeField(default=datetime.datetime.now)
    qemu_program = TextField('qemu-system-x86_64')
    bridge = TextField(default='br0')


class VirtBMC(BaseModel):
    vm = ForeignKeyField(QemuVM, related_name='vm')
    bmcname = TextField(unique=True)
    number = IntegerField()
    uuid = TextField()
    tmux_name = TextField()
    created_date = DateTimeField(default=datetime.datetime.now)
    listen_addr = TextField(default='127.0.0.1')
    ipmi_port = IntegerField(default=9001)
    fake_ipmi_mac_port = TextField()
    serial_port = IntegerField(default=9002)
    telnet_port = IntegerField(default=9003)
    lan_config_program = TextField()
    chassis_control_program = TextField()
    ipmi_sim = TextField()
    ipmi_config_file = TextField()
    status_file = TextField(default='/tmp/vbmc_qemu.status')
    ipmi_op_record_file = TextField()
    ipmiusr = TextField()
    ipmipass = TextField()


def _create_tables(tables):
    global DB
    DB.create_tables(tables)


def init_db():
    _create_tables([VirtBMC, QemuVM])


def remove_db():
    utils.rmfile(DB_FILE)


def manage(args):
    if args.init:
        init_db()
    if args.remove:
        remove_db()
