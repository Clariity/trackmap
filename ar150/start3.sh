#!/bin/ash

airmon-ng start wlan0
tcpdump -i mon0 -e type mgt subtype probe-req > output3.pcap & sleep 60; kill $!;
cat output3.pcap | ssh pi@192.168.8.154 -i .ssh/id_rsa "cat - > Documents/output3.pcap"
