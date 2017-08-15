#!/usr/bin/env python

import os

from uuid import uuid4
from tabulate import tabulate
from multiprocessing.pool import ThreadPool as Pool
from multiprocessing import Lock

from virtbmc.models import VirtBMC, QemuVM
from virtbmc.template import gen_template_content
from virtbmc.clrlog import LOG
import virtbmc.utils as utils
import virtbmc.config as config
from virtbmc import procutils


RUNNING_STATUS = 'running'
STOP_STATUS = 'stop'
ERROR_STATUS = 'error'


class QemuBMCUnit(object):

    def __init__(self, number, listen_addr, ipmi_port,
                 serial_port, telnet_port, qemu_program,
                 memory, ncpu, vncport, bridge, workspace,
                 image_size, ipmi_sim, ipmiusr, ipmipass,
                 uuid=None, **kwargs):
        self.uuid = uuid or str(uuid4())
        self.number = number
        self.bmcname = 'bmc--{}--{}'.format(
            self.uuid, self.number)
        self.qemuname = 'vm--{}--{}'.format(
            self.uuid, self.number
        )
        self.tmux_name = 'vbmc-{}--{}'.format(
            self.number, self.uuid[:8]
        )

        self.listen_addr = listen_addr
        self.ipmi_port = int(ipmi_port)
        self.fake_ipmi_mac_port = str(ipmi_port)[:2] + ':' + str(ipmi_port)[2:]
        self.serial_port = serial_port
        self.telnet_port = telnet_port
        self.path_prefix = '{}/{}--{}'.format(workspace, self.uuid, self.number)
        self.lan_config_program = '{}/ipmi_sim_lancontrol'.format(self.path_prefix)
        self.chassis_control_program = '{}/ipmi_sim_chassiscontrol'.format(self.path_prefix)
        self.ipmi_sim = ipmi_sim
        self.ipmi_config_file = '{}/lan.conf'.format(self.path_prefix)
        self.bmc_env_file = '{}/gen-bmc-env'.format(self.path_prefix)
        self.status_file = '{}/vbmc_qemu.status'.format(self.path_prefix)
        self.ipmi_op_record_file = '{}/operate.record'.format(self.path_prefix)
        self.ipmiusr = ipmiusr or 'root'
        self.ipmipass = ipmipass or 'test'

        self.qemu_program = qemu_program
        self.memory = memory
        self.ncpu = ncpu
        self.image_size = image_size
        self.disk = '{}/disks/{}.qcow2'.format(self.path_prefix, self.uuid)
        self.ifup_script = '{}/qemu-ifup'.format(self.path_prefix)
        self.ifdown_script = '{}/qemu-ifdown'.format(self.path_prefix)
        self.qemu_pidfile = '{}/qemu.pid'.format(self.path_prefix)
        self.controller_script = '{}/controller'.format(self.path_prefix)
        self.ifmac = kwargs.get('ifmac') or utils.random_mac()
        self.vncport = vncport
        self.bridge = bridge

    def _create_template_content(self, temfile, outfile):
        gen_template_content(temfile, outfile, self.__dict__)

    def gen_bmc_env(self, temfile):
        utils.mkdir_of_file(self.bmc_env_file)
        self._create_template_content(temfile, self.bmc_env_file)
        utils.make_executable(self.bmc_env_file)

    def gen_qemu_ifup(self, temfile):
        utils.mkdir_of_file(self.ifup_script)
        self._create_template_content(temfile, self.ifup_script)
        utils.make_executable(self.ifup_script)

    def gen_qemu_ifdown(self, temfile):
        utils.mkdir_of_file(self.ifdown_script)
        self._create_template_content(temfile, self.ifdown_script)
        utils.make_executable(self.ifdown_script)

    def gen_ipmi_sim_chassiscontrol(self, temfile):
        utils.mkdir_of_file(self.chassis_control_program)
        self._create_template_content(temfile, self.chassis_control_program)
        utils.make_executable(self.chassis_control_program)

    def gen_ipmi_lancontrol(self, temfile):
        utils.mkdir_of_file(self.lan_config_program)
        self._create_template_content(temfile, self.lan_config_program)
        utils.make_executable(self.lan_config_program)

    def gen_ipmi_config(self, temfile):
        utils.mkdir_of_file(self.ipmi_config_file)
        self._create_template_content(temfile, self.ipmi_config_file)

    def gen_controller_script(self, temfile, tmux_cmd):
        utils.mkdir_of_file(self.controller_script)
        self._create_template_content(temfile, self.controller_script)
        utils.make_executable(self.controller_script)
        utils.cpto(tmux_cmd, self.path_prefix)

    def gen_all_scripts(self, temdir):
        self.gen_bmc_env('{}/{}'.format(temdir, 'gen-bmc-env.tem'))
        self.gen_qemu_ifup('{}/{}'.format(temdir, 'qemu-ifup.tem'))
        self.gen_qemu_ifdown('{}/{}'.format(temdir, 'qemu-ifdown.tem'))
        self.gen_ipmi_sim_chassiscontrol('{}/{}'.format(temdir, 'ipmi_sim_chassiscontrol.tem'))
        self.gen_ipmi_lancontrol('{}/{}'.format(temdir, 'ipmi_sim_lancontrol.tem'))
        self.gen_ipmi_config('{}/{}'.format(temdir, 'lan.conf.tem'))
        self.gen_controller_script('{}/{}'.format(temdir, 'controller.tem'),
                              '{}/{}'.format(temdir, 'tmux-cmd'))

    def create_qemu_image(self):
        utils.mkdir_of_file(self.disk)
        cmd = ['qemu-img', 'create', '-f', 'qcow2', self.disk, self.image_size]
        utils.run_cmd(cmd)

    def run_bmc(self):
        if not self.is_bmc_running():
            cmd = [self.controller_script, 'start', self.ipmiusr, self.ipmipass]
            utils.run_cmd(cmd)
            LOG.info('Start BMC: {} DONE.'.format(self.bmcname))
        else:
            LOG.warning('BMC: {} already started.'.format(self.qemuname))

    def run_vm(self):
        try:
            if not self.is_vm_running():
                cmd = [self.controller_script, 'startvm', self.ipmiusr, self.ipmipass]
                utils.run_cmd(cmd)
                LOG.info('Starting VM: {} DONE.'.format(self.qemuname))
            else:
                LOG.warning('VM: {} already started.'.format(self.qemuname))
        except Exception as e:
            LOG.error("Run VM error: {}".format(e))

    def kill_qemu_by_pid(self):
        with open(self.qemu_pidfile, 'r') as f:
            pid = f.read().strip()
            procutils.check_call_no_exception(['kill', '-9', pid])

    def get_vm_status_byfile(self):
        import re
        info = {}
        if not os.path.exists(self.status_file):
            info['power'] = 'off'
            info['bootdev'] = 'default'
            return info
        with open(self.status_file) as f:
            for line in f.readlines():
                power_m = re.search(r'^power: (.*)', line.strip())
                bootdev_m = re.search(r'^bootdev: (.*)', line.strip())
                if power_m:
                    info['power'] = power_m.group(1)
                if bootdev_m:
                    info['bootdev'] = bootdev_m.group(1)
        return info

    def get_vm_status(self):
        if not os.path.exists(self.status_file):
            status = STOP_STATUS
        else:
            if self.get_vm_status_byfile().get('power', 'off') == 'off':
                status = STOP_STATUS
            else:
                cmd = 'ipmitool -I lanplus -U {} -P {} -H {} -p {} chassis power status'.format(self.ipmiusr, self.ipmipass,
                                                                                                self.listen_addr, self.ipmi_port).split()
                try:
                    output = utils.run_cmd(cmd)
                    if 'Power is on' in ''.join(output):
                        status = RUNNING_STATUS
                    else:
                        status = STOP_STATUS
                except:
                    status = ERROR_STATUS
        return status

    def get_bmc_status(self):
        if utils.is_port_open(self.ipmi_port):
            return RUNNING_STATUS
        else:
            return STOP_STATUS

    def is_vm_running(self):
            if self.get_vm_status() == RUNNING_STATUS:
                return True
            else:
                return False

    def is_bmc_running(self):
        if self.get_bmc_status() == RUNNING_STATUS:
            return True
        else:
            return False

    def stop_vm(self):
        if self.is_vm_running():
            cmd = [self.controller_script, 'stopvm', self.ipmiusr, self.ipmipass]
            utils.run_cmd(cmd)
            LOG.info('Stop VM: {} DONE.'.format(self.qemuname))
        if os.path.exists(self.qemu_pidfile):
            if self.get_vm_status() == ERROR_STATUS or procutils.check_pid_alive(self.qemu_pidfile, 'qemu'):
                self.kill_qemu_by_pid()
                LOG.warning("VM: {} be killed".format(self.qemuname))
        else:
            LOG.warning('VM: {} already stopped.'.format(self.qemuname))

    def stop_bmc(self):
        if self.is_bmc_running:
            cmd = [self.controller_script, 'stop', self.ipmiusr, self.ipmipass]
            utils.run_cmd(cmd)
            LOG.info('Stop BMC: {} DONE.'.format(self.qemuname))
        else:
            LOG.warning('BMC: {} already stopped.'.format(self.qemuname))


    def save_todb(self):
        qemuvm = QemuVM(**self.__dict__)
        vbmc = VirtBMC(vm=qemuvm, **self.__dict__)
        qemuvm.save()
        vbmc.save()

    def cleanup(self):
        self.stop_vm()
        self.stop_bmc()
        utils.rmdirs(self.path_prefix)


    list_headers = ['Order', 'UUID', 'TmuxSession',
                    'ListenIp', 'IPMIPort', 'VncPort', 'VmMAC',
                    'IPMIUser', 'IPMIPassword', 'BMCStatus',
                    'VMStatus', 'BootDev']

    def get_list_field(self):
        return [
            self.number,
            self.uuid,
            self.tmux_name,
            self.listen_addr,
            self.ipmi_port,
            5900+self.vncport,
            self.ifmac,
            self.ipmiusr,
            self.ipmipass,
            self.get_bmc_status(),
            self.get_vm_status(),
            self.get_vm_status_byfile()['bootdev'],
        ]


BMC_FREE_PORT = utils.get_free_port(9000, 9500)
VNC_FREE_PORT = utils.get_free_port(5900, 6000)


def gen_config(args, num):
    global BMC_FREE_PORT
    global VNC_FREE_PORT
    db_items = VirtBMC.select().order_by(VirtBMC.number)
    if len(db_items) != 0:
        used_bmc_port = [item.ipmi_port for item in db_items]
        used_bmc_port += [item.ipmi_port for item in db_items]
        used_bmc_port += [item.telnet_port for item in db_items]
        used_vnc_port = [5900+item.vm.vncport for item in db_items]

        BMC_FREE_PORT = list(set(BMC_FREE_PORT)-set(used_bmc_port))
        VNC_FREE_PORT = list(set(VNC_FREE_PORT)-set(used_vnc_port))
    res = {}
    res['number'] = num
    res['ipmi_sim'] = args.ipmi_sim
    res['listen_addr'] = utils.get_netiface_ip(args.bridge)
    ipmi_udp_port = BMC_FREE_PORT.pop(0)
    serial_tcp_port = ipmi_udp_port
    res['ipmi_port'] = ipmi_udp_port
    res['serial_port'] = serial_tcp_port
    res['telnet_port'] = BMC_FREE_PORT.pop(0)
    res['vncport'] = VNC_FREE_PORT.pop(0) - 5900
    res['qemu_program'] = args.qemu
    res['memory'] = args.memory
    res['ncpu'] = args.ncpu
    res['bridge'] = args.bridge
    res['workspace'] = config.WORKSPACE
    res['image_size'] = args.image_size
    res['ipmiusr'] = args.ipmi_user
    res['ipmipass'] = args.ipmi_password

    return res


def get_QemuBMC_unit(_uuid, **kwargs):
    vbmc = VirtBMC.get(VirtBMC.uuid == _uuid)
    vm = QemuVM.get(QemuVM.uuid == _uuid)
    if kwargs.get('ipmi_user', False) and vbmc.ipmiusr != kwargs['ipmi_user']:
        vbmc.ipmiusr = kwargs['ipmi_user']
        vbmc.save()
    if kwargs.get('ipmi_password', False) and vbmc.ipmipass != kwargs['ipmi_password']:
        vbmc.ipmipass = kwargs['ipmi_password']
        vbmc.save()
    res = vbmc.__dict__['_data'].copy()
    res.update(vm.__dict__['_data'])
    res['workspace'] = config.WORKSPACE
    return QemuBMCUnit(**res), vbmc, vm


def process_map(func, lst):
    if len(lst) == 0:
        LOG.info("Empty list..., skip")
        return
    pool = Pool(processes=len(lst))
    return pool.map(func, lst)


def create(args):

    def BMC_min_num():
        db_items = VirtBMC.select().order_by(VirtBMC.number)
        if len(db_items) == 0:
            return 0
        num_lst = [item.number for item in db_items]
        min_con_range = list(utils.ranges(num_lst))[0]
        if min_con_range[0] != 0:
            return 0
        else:
            return min_con_range[-1] + 1

    def _create(args, lock):
        with lock:
            res = gen_config(args, BMC_min_num())
            unit = QemuBMCUnit(**res)
            unit.save_todb()
        LOG.info(unit.__dict__)
        unit.gen_all_scripts(args.template)
        unit.create_qemu_image()

    lock = Lock()
    process_map(lambda _: _create(args, lock), range(0, args.number))


def extract_ipmi_user_passwd(args):
    ret = {}
    if args.ipmi_user:
        ret['ipmi_user'] = args.ipmi_user
    if args.ipmi_password:
        ret['ipmi_password'] = args.ipmi_password
    return ret


def list_all(args):
    uuids = [bmc.uuid for bmc in VirtBMC.select().order_by(VirtBMC.number)]
    print_table(uuids, args.json)

def print_table(ids, json_output):
    data_series = []

    for _uuid in ids:
        unit_item, _, _ = get_QemuBMC_unit(_uuid)
        data_series.append(unit_item.get_list_field())

    if json_output:
        import json
        output = [dict(zip(QemuBMCUnit.list_headers, item)) for item in data_series]
        output = json.dumps(output, indent=4)
    else:
        output = tabulate(data_series, QemuBMCUnit.list_headers,
                      tablefmt="psql")
    print(output)


def update(args):

    def _update(uuid):
        kwargs = extract_ipmi_user_passwd(args)
        unit_item, _, _ = get_QemuBMC_unit(uuid, **kwargs)

    if args.id[0] == 'all':
        update_list = [item.uuid for item in VirtBMC.select()]
    else:
        update_list = args.id

    process_map(_update, update_list)
    print_table(update_list, args.json)


def delete(args):
    def _delete(uuid):
        unit_item, bmc, vm = get_QemuBMC_unit(uuid)
        unit_item.cleanup()
        vm.delete_instance()
        bmc.delete_instance()

    if args.id[0] == 'all':
        delete_list = [item.uuid for item in VirtBMC.select()]
    else:
        delete_list = args.id

    process_map(_delete, delete_list)


def stop(args):
    def _stop(uuid):
        unit_item, bmc, vm = get_QemuBMC_unit(uuid)
        unit_item.stop_vm()
        unit_item.stop_bmc()

    if args.id[0] == 'all':
        stop_list = [item.uuid for item in VirtBMC.select()]
    else:
        stop_list = args.id

    process_map(_stop, stop_list)


def start(args):
    def _start(uuid):
        unit_item, _, _ = get_QemuBMC_unit(uuid)
        unit_item.run_bmc()
        if args.autostart_vm:
            unit_item.run_vm()

    if args.bmc[0] == 'all':
        bmc_list = [item.uuid for item in VirtBMC.select()]
    else:
        bmc_list = args.start_bmc

    map(_start, bmc_list)
