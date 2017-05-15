#!/bin/bash

sed -i 's/jessie/stretch/g' /etc/apt/sources.list
apt-get -y update
apt-get -y upgrade
apt-get -y dist-upgrade
