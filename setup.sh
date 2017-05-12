#!/bin/bash

# This script is supposed to be run on a clean machine and will handle all
# setup. The first argument needs to be the path to a directory with the
# needed ssh keys to clone all repositories. They should be copied onto the
# machine and been given the correct permissions so that ssh won't complain
# (for example `chmod -R 600 /keys`). The folder will be deleted by this
# script after setup.

# Use the SSH key for all git commands
export SSH_KEY_DIR="$1"

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
