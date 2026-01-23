#!/usr/bin/env python3
import errno
import sys
from scapy.all import sniff, IP, TCP, UDP, Raw
import os

def check_root():
    if os.getuid() != 0:
        print("Must be run as root", file=sys.stderr)
        sys.exit(errno.EPERM)

def handle_packet(pkt):
    if IP not in pkt or TCP not in pkt:
        return

    ip = pkt[IP]
    tcp = pkt[TCP]
    print(ip.src, ip.dst, tcp.sport, tcp.dport)


if __name__ == '__main__':
    check_root()
    try:
        sniff(
                # sniff localhost only
                iface="lo",
                filter="ip and tcp and host 127.0.0.1",
                prn=handle_packet,
                store=0,
                )
    except KeyboardInterrupt:
        pass
    
