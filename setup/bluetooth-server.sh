#!/bin/bash
apt-get install -y python python-dev python-pip libbluetooth-dev expect

cd bluetooth-server
pip install -r requirements.txt

# Just need any SSH key because the repo is public
GIT_SSH_COMMAND="ssh -i $SSH_KEY_DIR/linespace-raspberry" git clone --depth=1 git@github.com:boeckhoff/silhouette.git silhouette
cd silhouette
python setup.py install

# Fix bluetooth (https://www.raspberrypi.org/forums/viewtopic.php?f=63&t=133263)
sed -i 's:\(ExecStart=.*\):\1:' /etc/systemd/system/dbus-org.bluez.service
sdptool add SP

cd ../..
