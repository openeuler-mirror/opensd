#!/usr/bin/env python
#coding:utf-8

import argparse
import copy
import commands
import os
import re

from oslo_log import log as logging
LOG = logging.getLogger(__name__)

def get_vgpu_pin_set(reserve_vgpu_nums):
   vgpu_set = []
   vgpu_pin_set = ""

   cmd = "lscpu |grep 'NUMA node[0-9] CPU(s)' | awk '{print $NF}' | tr ',' '\n'"
   (status, outputline) = commands.getstatusoutput(cmd)
   if 0 != status:
       raise Exception(str(outputline))
   if "" == outputline:
       raise Exception("cmd output should not be empty")
   outputdata = outputline.split("\n")
   numa_nodes = len(outputdata)
   zheng = reserve_vgpu_nums / numa_nodes
   yu = reserve_vgpu_nums % numa_nodes
   for data in outputdata:
       data_s = map(eval, data.split("-"))
       if yu != 0:
           yu -= 1
           data_s[0] = data_s[0] + zheng + 1
       else:
           data_s[0] = data_s[0] + zheng
       data_snew="-".join([str(x) for x in data_s])
       vgpu_set.append(data_snew)
   print (str(",".join(vgpu_set)))

def main():
    parser = argparse.ArgumentParser(description='''Creates a list of cron
        intervals for a node in a group of nodes to ensure each node runs
        a cron in round robin style.''')
    parser.add_argument('-n', '--number',
                        help='Number of reserve processores',
                        required=True,
                        type=int)
    args = parser.parse_args()

    try:
        pin_set = get_vgpu_pin_set(args.number)
    except Exception as e:
        LOG.info('get_reserve_vgpu_nums : get_reserve_vgpu_nums failed error info is :: %s', str(e))
        return False

if __name__ == "__main__":
    main()

