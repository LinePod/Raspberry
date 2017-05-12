#!/bin/bash
apt-get install -y python python-dev python-pip libbluetooth-dev expect

cd bluetooth-server
pip install -r requirements.txt

# Just need any SSH key because the repo is public
GIT_SSH_COMMAND="ssh -i $SSH_KEY_DIR/linespace-raspberry" git clone --depth=1 git@github.com:vishnubob/silhouette.git silhouette
cd silhouette
python setup.py install

cd ../..
