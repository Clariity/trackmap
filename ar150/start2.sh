#!/bin/ash

airmon-ng start wlan0
tcpdump -i mon0 -e type mgt subtype probe-req > output2.pcap & sleep 60; kill $!;
cat output2.pcap | ssh pi@192.168.8.154 -i .ssh/id_rsa "cat - > Documents/output2.pcap"
