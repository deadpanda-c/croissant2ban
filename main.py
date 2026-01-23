#!/usr/bin/env python3
import errno
import sys
from scapy.all import sniff, IP, TCP, UDP, Raw
import os
import json

def check_root():
    if os.getuid() != 0:
        print("Must be run as root", file=sys.stderr)
        raise SystemExit(errno.EPERM)

def handle_packet(pkt):
    if IP not in pkt or TCP not in pkt:
        return

    ip = pkt[IP]
    tcp = pkt[TCP]
    print(ip.src, ip.dst, tcp.sport, tcp.dport)

def init_config():
    with open('conf/croissant.json') as f:
        config = json.load(f)

    for service in config['services'].values():
        try:
            if service['enabled'] and service['enabled'] == True:
                print("Starting service...")
        except KeyError:
            print("Service not enabled")
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
    
