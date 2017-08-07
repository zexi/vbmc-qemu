#!/usr/bin/env python

from string import Template


class ScriptTemplate(Template):
    delimiter = '&'


def sub_template_string(content, kw):
    return ScriptTemplate(content).substitute(kw)


def gen_template_content(temfile, outfile, kw):
    with open(temfile, 'r') as f:
        content = f.read()
    gen_content = sub_template_string(content, kw)
    with open(outfile, 'w') as f:
        f.write(gen_content)

if __name__ == '__main__':
    ipmi_conf_temp = '../templates/lan.conf.tem'
    ipmi_conf_kw = {
        'listen_addr': '172.18.9.10',
        'ipmi_port': '9001',
        'lan_config_program': '../ipmi_sim_lancontrol',
        'bridge': 'br0',
        'fake_ipmi_mac_port': '90:01',
        'chassis_control_program': '../ipmi_sim_chassiscontrol',
        'serial_port': '9002',
        'telnet_port': '9003',
    }

    gen_template_content(ipmi_conf_temp, './out.res', ipmi_conf_kw)
