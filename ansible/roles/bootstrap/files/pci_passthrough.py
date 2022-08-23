#!/usr/bin/env python
#coding:utf-8

import copy
import re
import subprocess
import os

from oslo_log import log as logging
LOG = logging.getLogger(__name__)

DEFAULT_GPU_PATH = {
    "EFI_PATH": "/sys/firmware/efi",
    "GRUB_PATH": "/etc/sysconfig/grub",
    "VFIO_PATH": "/etc/modules-load.d/vfio.conf",
    "BLACKLIST_PATH": "/etc/modprobe.d/blacklist.conf",
    "VFIO_DEVICE_PATH": "/etc/modprobe.d/vfio.conf"
}

# "Tesla T4", "Tesla V100", "Tesla V100S" correspond to '1eb8', '1db4', '1df6'
DEAFULT_DEV_MAP = {
    "NVIDIA": ['1eb8', '1db4', '1df6']
}

DEFAULT_BLACK_LIST = {
    "NVIDIA": ["blacklist nouveau",
              "blacklist nvidia"],

    "AMD": ["blacklist amdgpu",
            "blacklist amdkfd",
            "blacklist radeon"]
}

DEFAULT_GRUB_ADD_INFO = [
    "intel_iommu=on",
    "rd.driver.pre=vfio-pci",
    "pci=realloc"
]

DEFAULT_VFIO_CONF_ADD_INFO =[
    'vfio',
    'vfio_iommu_type1',
    'vfio_pci'
]

DEAULT_SUPPORT_PRODUCT = [
    '1eb8',
    '1db4',
    '1df6'
]

class PciPhyPassTroughDriver(object):

    def __init__(self):
        self.dev_name_list = []
        self.dev_pvid_addr_dict = {}
        self.pid_vid_set = set()
        self.blacklist_list = []
        self.vfio_conf_list = []

    def _load_pci_dev(self):
        self.dev_name_list = DEAULT_SUPPORT_PRODUCT

    def _remove_pci_dev(self):
        self.dev_name_list = []
        self.dev_pvid_addr_dict = {}
        self.pid_vid_set = set()
        self.blacklist_list = []
        self.vfio_conf_list = []

    def _get_pid_vid_by_name(self):
        try:
            cmd = 'lspci -nn'
            (status, outputline) = subprocess.getstatusoutput(cmd)
            if 0 != status:
                raise Exception(str(outputline))

            for dev_name in self.dev_name_list:
                pid_vid = None
                temp_addr_list = []
                for data in outputline.split("\n"):
                    if dev_name in data:
                        pci_address = data.split()[0]
                        temp_addr_list.append(pci_address)
                        pid_vid = data.split()[-3].split('[')[1].split(']')[0]
                        self.pid_vid_set.add(pid_vid)

                if pid_vid is not None:
                    temp_name_pvid = dev_name + "_" + pid_vid
                    self.dev_pvid_addr_dict[temp_name_pvid] = temp_addr_list

            return True

        except Exception as e:
            LOG.info('set_pci_through : _get_pid_vid_by_name failed error info is :: %s', str(e))
            return False

    def _get_pid_vid_by_iommu_grp(self):
        try:
            self._load_pci_dev()

            cmd = 'lspci -nn'
            (status, outputline) = subprocess.getstatusoutput(cmd)
            if 0 != status:
                raise Exception(str(outputline))

            temp_addr_list = []
            for dev_name in self.dev_name_list:
                pid_vid = None
                temp_addr_list = []
                for data in outputline.split("\n"):
                    if "NVIDIA Corporation" in data:
                        pci_address = data.split()[0]
                        temp_addr_list.append(pci_address)
                        pid_vid = data.split()[-3].split('[')[1].split(']')[0]
                        self.pid_vid_set.add(pid_vid) # Get the pid and vid of current pci dev

            temp_child_addr_list = []
            for pci_addr in temp_addr_list:
                parent_addr = "0000:" + pci_addr
                iommu_group_path = "/sys/bus/pci/devices/" + parent_addr + "/iommu_group/devices/"
                for root, dirs, files in os.walk(iommu_group_path):
                    for pci_dev_addr in dirs:
                        if pci_dev_addr != parent_addr:
                            temp_child_addr = pci_dev_addr.split(":")[1]
                            temp_child_addr.append(temp_child_addr)

            for pci_addr in temp_child_addr_list:
                for data in outputline.split("\n"):
                    if pci_addr in data:
                        pci_address = data.split()[0]
                        pid_vid = data.split()[-3].split('[')[1].split(']')[0]
                        self.pid_vid_set.add(pid_vid) # Get the pid and vid of one group of current pci dev

            return True
        except Exception as e:
            LOG.info('set_pci_through : _get_pid_vid_by_name failed error info is :: %s', str(e))
            return False

    def _get_black_list_by_name(self):
        try:
            temp_blacklist_list = []
            temp_company_name_list = []
            for key,value_list in DEAFULT_DEV_MAP.items():
                for dev_name in value_list:
                    if dev_name in self.dev_name_list:
                        temp_company_name_list.append(key)
                        break

            for company_name in temp_company_name_list:
                for key,blacklist_list in DEFAULT_BLACK_LIST.items():
                    if key == company_name:
                        temp_blacklist_list.extend(blacklist_list)

            self.blacklist_list = temp_blacklist_list
            return True
        except Exception as e:
            LOG.info('set_pci_through : _get_black_list_by_name failed error info is :: %s', str(e))
            return False

    def _set_grub_config(self):

        rewrite_flag = False
        try:
            with open(DEFAULT_GPU_PATH.get("GRUB_PATH"), 'a+') as f:
                f.seek(0)
                grub_item_list = f.readlines()
                grub_old_item = ''.join([value for value in grub_item_list if re.search('GRUB_CMDLINE_LINUX',value)])
                grub_new_item = copy.deepcopy(grub_old_item).strip().replace("GRUB_CMDLINE_LINUX=",'').split('\"')[1]

                for add_item in DEFAULT_GRUB_ADD_INFO:
                    if add_item not in grub_new_item:
                        rewrite_flag = True
                        grub_new_item += ' ' + add_item

                if rewrite_flag is False:
                    return True

                grub_new_item = "GRUB_CMDLINE_LINUX=" + '\"' + grub_new_item + '\"' + '\n'

                grub_item_list.remove(grub_old_item)
                grub_item_list.insert((len(grub_item_list)-1), grub_new_item)

                f.seek(0)  
                f.truncate()
                f.write(''.join(grub_item_list))

            return True
        except Exception as e:
            LOG.info('set_pci_through : _set_grub_config failed error info is :: %s', str(e))
            return False

    def _rebuild_grub_file(self):
        try:
            if os.path.isdir(DEFAULT_GPU_PATH.get("EFI_PATH")):
                cmd = 'grub2-mkconfig -o /boot/efi/EFI/centos/grub.cfg'
            else:
                cmd = 'grub2-mkconfig -o /boot/grub2/grub.cfg'

            (status, output) = subprocess.getstatusoutput(cmd)
            if 0 != status:
                raise Exception(str(output))
            return True

        except Exception as e:
            LOG.info('set_pci_through : _rebuild_grub_file failed error info is :: %s', str(e))
            return False

    def _add_data_into_file(self,path,data):
        try:
            with open(path, 'a+') as f:
                f.seek(0)
                f.truncate()
                f.write(data)
            return True
        except Exception as e:
            LOG.info('GPU_passThrough_set_vfio_config failed error info is :: %s', str(e))
            return False

    def _get_vfio_conf(self):
        self.vfio_conf_list = DEFAULT_VFIO_CONF_ADD_INFO

    def _set_vfio_config(self):
        try:
            data = '\n'.join(self.vfio_conf_list)
            return self._add_data_into_file(DEFAULT_GPU_PATH.get("VFIO_PATH"), data)
        except Exception as e:
            LOG.info('set_pci_through : _set_vfio_config failed error info is :: %s', str(e))
            return False

    def _set_backlist(self,para=[]):
        try:
            data = '\n'.join(self.blacklist_list)
            return self._add_data_into_file(DEFAULT_GPU_PATH.get("BLACKLIST_PATH"), data)
        except Exception as e:
            LOG.info('set_pci_through : _set_backlist failed error info is :: %s', str(e))
            return False

    def _set_device_into_vfio(self):
        try:
            add_item_list = list(self.pid_vid_set)
            if len(add_item_list):
                data = 'options vfio-pci ids=' + ','.join(add_item_list).strip(',')
            else:
                data = ''
            return self._add_data_into_file(DEFAULT_GPU_PATH.get("VFIO_DEVICE_PATH"), data)
        except Exception as e:
            LOG.info('set_pci_through : _set_device_into_vfio failed error info is :: %s', str(e))
            return False

    def _rebuild_initraft(self):

        try:
            (status, output) = subprocess.getstatusoutput('uname -r')
            if 0 != status:
                raise Exception(str(status))

            original_path = "/boot/initramfs-" + output + ".img"
            back_path = "/boot/initramfs-" + output + ".img.bk"
            if os.path.exists(back_path) is True:
                os.remove(back_path)
            
            cmd = "cp" + "  " + original_path + " " + back_path 
            (status, output) = subprocess.getstatusoutput(cmd)
            if 0 != status:
                raise Exception(str(output))

            cmd = "dracut -v /boot/initramfs-$(uname -r).img $(uname -r) --force"
            (status, output) = subprocess.getstatusoutput(cmd)
            if 0 != status:
                raise Exception(str(output))

            cmd = "sync && sync"
            (status, output) = subprocess.getstatusoutput(cmd)
            if 0 != status:
                raise Exception(str(output))

            cmd = "echo 3 > /proc/sys/vm/drop_caches"
            (status, output) = subprocess.getstatusoutput(cmd)
            if 0 != status:
                raise Exception(str(output))

            return True
        except Exception as e:
            LOG.info('set_pci_through : _rebuild_initraft failed error info is :: %s', str(e))
            return False

    def _rollback_set_passthrough(self):
        try:
            self._remove_pci_dev()

            self._set_vfio_config()
            self._set_backlist()
            self._set_device_into_vfio()
            self._rebuild_initraft()
        except Exception as e:
            LOG.info('set_pci_through : _rollback_set_passthrough failed error info is :: %s', str(e))
            return False

    def set_pci_devs_passthrough(self):
        try:

            self._load_pci_dev()

            self._set_grub_config()
            self._rebuild_grub_file()

            self._get_vfio_conf()
            self._set_vfio_config()

            self._get_black_list_by_name()
            self._set_backlist()

            self._get_pid_vid_by_iommu_grp()
            self._set_device_into_vfio()

            self._rebuild_initraft()

        except Exception as e:
            LOG.info('set_pci_through : set_pci_devs_passthrough failed error info is :: %s', str(e))
            self._rollback_set_passthrough()
            return False

    def remove_pci_devs_passthrough(self):
        return self._rollback_set_passthrough()

if __name__ == '__main__':
    obj = PciPhyPassTroughDriver()
    #obj.remove_pci_devs_passthrough()
    obj.set_pci_devs_passthrough()
    #obj._get_pid_vid_by_iommu_grp()

