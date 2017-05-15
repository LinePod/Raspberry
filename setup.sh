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

apt-get update -y
apt-get install -y git

# Add ssh identity of github.com
mkdir -p ~/.ssh
touch ~/.ssh/known_hosts
ssh-keyscan github.com >> ~/.ssh/known_hosts

GIT_SSH_COMMAND="ssh -i $SSH_KEY_DIR/linespace-raspberry" git clone --depth=1 git@github.com:boeckhoff/linespace_raspberry.git ~/linespace
cd ~/linespace
setup/setup.sh
rm -r "$SSH_KEY_DIR"
