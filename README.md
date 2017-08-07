# virtual BMC with qemu

[OpenIPMI](https://sourceforge.net/projects/openipmi) and [Qemu](https://github.com/qemu/qemu) BMC IPMI emulations.

More info to view: <http://www.linux-kvm.org/images/7/76/03x08-Juniper-Corey_Minyard-UsingIPMIinQEMU.ods.pdf>

## Install

Only test on Centos7

```sh
# install Qemu & OpenIPMI build essentials
$ yum install -y $(cat ./tools/require-rpms.txt)

# build and install Qemu & OpenIPMI
# you can ignore below steps if already install qemu >= 2.6 and OpenIPMI
$ ./tools/install-qemu.sh
$ ./tools/install-openipmi.sh

# after build, you can see qemu and openipmi in /opt
$ ls -alh /opt/openipmi/bin/
...
-rwxr-xr-x 1 root root 593K Aug 15 00:03 ipmi_sim
...

$ ls -alh /opt/qemu2.7/bin/
...
-rwxr-xr-x 1 root root 8.9M Aug 15 00:20 qemu-system-x86_64
...
# Ensure qemu-img is in $PATH
$ export PATH=$PATH:/opt/qemu2.7/bin/

# install python requirements
$ pip install -r requirements.txt
```

## Prepare

Before the emulation, we should create a bridge interface

```sh
$ sudo brctl addbr br0
$ sudo ip addr add 10.0.2.1/24 dev br0
```

## Usage

```sh
# Init sqlite database to store ipmi and qemu metadata
$ ./vbmc.py db --init

# Create one Vm with BMC
$ ./vbmc.py create -n 1

# List created Vm
$ ./vbmc.py list

# Start all or <id>
$ ./vbmc.py start all --autostart-vm

# Delete all or <id>
$ ./vbmc.py delete all
```

### check background qemu process

```sh
$ ps faux | grep qemu-system
root      48660 10.2  0.9 5956108 37312 ?       Sl   00:58   0:15 /opt/qemu2.7/bin/qemu-system-x86_64 -m 4096 -smp 1 -boot nd -drive if=none,id=hd0,file=/data/code/vbmc-qemu/workspace/bf83a2ed-1028-4742-ab7d-212b9583885e--0/disks/bf83a2ed-1028-4742-ab7d-212b9583885e.qcow2 -device virtio-scsi-pci,id=scsi0 -device scsi-hd,bus=scsi0.0,id=scsi0-0,drive=hd0 -netdev tap,id=network0,script=/data/code/vbmc-qemu/workspace/bf83a2ed-1028-4742-ab7d-212b9583885e--0/qemu-ifup,downscript=/data/code/vbmc-qemu/workspace/bf83a2ed-1028-4742-ab7d-212b9583885e--0/qemu-ifdown -device e1000,netdev=network0,mac=00:16:3e:6d:9b:1f -chardev socket,id=ipmi0,host=10.0.2.1,port=9000,reconnect=10 -device ipmi-bmc-extern,id=bmc0,chardev=ipmi0 -device isa-ipmi-bt,bmc=bmc0 -serial mon:telnet::9001,server,telnet,nowait -vnc :0 -daemonize --pidfile /data/code/vbmc-qemu/workspace/bf83a2ed-1028-4742-ab7d-212b9583885e--0/qemu.pid
```

### Supported commands

```sh
# At first, check the VM and BMC metadata
$ ./vbmc.py list --json
[
    {
        "Listen Ip": "10.0.2.1",
        "VM Status": "running pxe",
        "UUID": "bf83a2ed-1028-4742-ab7d-212b9583885e",
        "Listen Port": "ipmi:9000 vnc:5900",
        "BMC status": "running",
        "number": 0,
        "Tmux Session": "vbmc-0--bf83a2ed",
        "Vm MAC": "00:16:3e:6d:9b:1f",
        "IPMI User": "root",
        "IPMI Password": "test"
    }
]

# Power on or off the vm
$ ipmitool -I lanplus -H 10.0.2.1 -p 9000 -U root -P test power on|off

# Check the power status
$ ipmitool -I lanplus -H 10.0.2.1 -p 9000 -U root -P test power status

# Set the boot device to network, hd or cdrom
$ ipmitool -I lanplus -U admin -P password -H 127.0.0.1 chassis bootdev pxe|disk|cdrom
```
