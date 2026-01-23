#!/usr/bin/env python3
import errno
import sys
from scapy.all import sniff, IP, TCP, UDP, Raw

def check_root():
    if os.getuid() != 0:
        print("Must be run as root", file=sys.stderr)
        sys.exit(errno.EPERM)

if __name__ == '__main__':
    check_root()
    
