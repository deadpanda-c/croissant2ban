#!/usr/bin/env python3
import errno
import sys
from scapy.all import sniff, IP, TCP, UDP, Raw
import os
import json
import logging

CONFIG_FILE = 'conf/croissant.json'
logging.basicConfig(level=logging.DEBUG)

def check_root():
    if os.getuid() != 0:
        print("Must be run as root", file=sys.stderr)
        raise SystemExit(errno.EPERM)

def handle_packet(pkt):
    if IP not in pkt or TCP not in pkt:
        return

    ip = pkt[IP]
    tcp = pkt[TCP]
    # print(ip.src, ip.dst, tcp.sport, tcp.dport)
    logging.info("Got packet from %s to %s", ip.src, ip.dst)

def init_config():
    with open(CONFIG_FILE) as f:
        config = json.load(f)

    for service in config['services'].values():
        try:
            if service['enabled'] and service['enabled'] == True:
                logging.info("Starting service %s", service['name'])
            else:
                logging.info("Service %s is disabled", service['name'])
        except KeyError:
            logging.info("Service %s is disabled", service['name'])
            continue

if __name__ == '__main__':
    check_root()
    try:
        init_config()
        # sniff(
        #         iface="lo",
        #         filter="ip and tcp and host 127.0.0.1",
        #         prn=handle_packet,
        #         store=0,
        #         )
    except KeyboardInterrupt:
        pass
    
