#!/usr/bin/env python3
import sys
import os.path
import glob
import csv
import bz2
import os.path

from scapy.all import sniff

from artichoke.parser import parse_oui_file, parse_packet


if __name__ == '__main__':
    in_path_rule = '/Users/mac/Documents/data/office/pcap/*.pcap'
    out_path_folder = '/Users/mac/Documents/data/office/csv/'
    filter = 'subtype probe-req or type data'
    pkt_header = set(
        'Antenna,Channel,Flags,Rate,TSFT,cname,dBm_AntSignal,da,elt_vendor,oui,rt,sa,sn,ssid,subtype,type'.split(','))

    oui2company = parse_oui_file('./data/wifi_oui_list.txt')

    for in_file_path in glob.glob(in_path_rule):
        filename, *_ = os.path.basename(in_file_path).rsplit('.', 1)
        out_file_path = os.path.join(out_path_folder, filename + '.csv.bz2')
        print(filename)
        with bz2.open(out_file_path, 'wt') as f:
            writer = csv.DictWriter(f, fieldnames=pkt_header)
            writer.writeheader()
            sniff(offline=in_file_path,
                  filter=filter,
                  store=0,
                  prn=lambda pkt: writer.writerow({k: v for k, v in parse_packet(pkt, oui2company).items() if k in pkt_header}))
