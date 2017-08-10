#!/bin/bash
apt-get install -y python python-dev python-pip libbluetooth-dev expect

cd bluetooth-server
pip install -r requirements.txt

cd silhouette
python setup.py install

# Fix bluetooth (https://www.raspberrypi.org/forums/viewtopic.php?f=63&t=133263)
#
# Creates a new systemd unit file in /etc/systemd/system, that overrides the
# default one
cp /lib/systemd/system/bluetooth.service /etc/systemd/system/bluetooth.service
sed -i "s:\(ExecStart=.*\):\1 --compat\nExecStartPost=$(which sdptool) add SP:" /etc/systemd/system/bluetooth.service

cd ../..

# Create new systemd service for the server
cp setup/units/linepod.server.template.service /etc/systemd/system/linepod.server.service
sed -i "s:__INSTALL_ROOT__:$(pwd):" /etc/systemd/system/linepod.server.service
systemctl daemon-reload
systemctl enable linepod.server
