#!/bin/bash

# This script is supposed to be run on a clean machine and will handle all
# setup. The first argument needs to be the path to a directory with the
# needed ssh keys to clone all repositories. They will be copied into a
# temporary directory, given the right access rights so that ssh doesn't
# complain and deleted later (only the copy).

# Setup ssh keys
export SSH_KEY_DIR=$(mktemp -d)
cp -R "${1}/." $SSH_KEY_DIR
chmod -R 600 $SSH_KEY_DIR

# Check whether we are on a pi or in a virtual machine
if [[ "$(uname -m)" == "arm*" ]]; then
    export IS_PI='true'
fi

# Upgrade to debian stretch
# We upgrade here to have a git >= 2.3.0, so we can use GIT_SSH_COMMAND.
sed -i 's/jessie/stretch/g' /etc/apt/sources.list
apt-get -y update
apt-get -y upgrade
apt-get -y dist-upgrade

# Install git
apt-get -y install git

# Add ssh identity of github.com
mkdir -p ~/.ssh
touch ~/.ssh/known_hosts
ssh-keyscan github.com >> ~/.ssh/known_hosts

GIT_SSH_COMMAND="ssh -i $SSH_KEY_DIR/linespace-raspberry" git clone --depth=1 git@github.com:boeckhoff/linespace_raspberry.git ~/linespace
cd ~/linespace
setup/setup.sh

# Cleanup and reboot
rm -r "$SSH_KEY_DIR"
reboot now
