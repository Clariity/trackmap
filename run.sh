#!/bin/bash

screen -dm bash -c 'ssh root@192.168.8.1 ./start.sh; exec sh'
screen -dm bash -c 'ssh root@192.168.8.2 ./start.sh; exec sh'
screen -dm bash -c 'ssh root@192.168.8.3 ./start.sh; exec sh'
sleep 70;
echo "done"
