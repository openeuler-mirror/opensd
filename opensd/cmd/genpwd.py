#!/usr/bin/env python

import argparse
import os
import random
import string
import sys

from oslo_utils import uuidutils
import yaml

PROJECT_ROOT = os.path.abspath(os.path.join(
    os.path.dirname(os.path.realpath(__file__)), '../..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-p', '--passwords', type=str,
        default=os.path.abspath('/etc/opensd/passwords.yml'),
        help=('Path to the passwords.yml file'))

    args = parser.parse_args()
    passwords_file = os.path.expanduser(args.passwords)

    # These keys should be random uuids
    uuid_keys = ['nova_ceph_client_uuid']

    # length of password
    length = 40

    with open(passwords_file, 'r') as f:
        passwords = yaml.safe_load(f.read())

    for k, v in passwords.items():
        if v is None:
            if k in uuid_keys:
                passwords[k] = uuidutils.generate_uuid()
            else:
                passwords[k] = ''.join([
                    random.SystemRandom().choice(
                        string.ascii_letters + string.digits)
                    for n in range(length)
                ])

    with open(passwords_file, 'w') as f:
        f.write(yaml.safe_dump(passwords, default_flow_style=False))

if __name__ == '__main__':
    main()
