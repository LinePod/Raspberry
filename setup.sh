#!/bin/bash

# This script is supposed to be run on a clean machine and will handle all
# setup. It needs to be run with admin priviliges and will install everything
# in a linespace folder in the home folder of the root user (commonly /root)

# Check whether we are on a pi or in a virtual machine
if [[ "$(uname -m)" == "arm*" ]]; then
    export IS_PI='true'
fi

# Upgrade to debian stretch
# See https://serverfault.com/questions/48724/100-non-interactive-debian-dist-upgrade
# for how to do a noninteractive dist-upgrade
export DEBIAN_FRONTEND=noninteractive
export APT_LISTCHANGES_FRONTEND=none
sed -i 's/jessie/stretch/g' /etc/apt/sources.list
apt-get -y update
apt-get -fy -o Dpkg::Options::="--force-confnew" --force-yes upgrade
apt-get -fy -o Dpkg::Options::="--force-confnew" --force-yes dist-upgrade

# Install git
apt-get -y install git

# Tell git to use unauthenticated cloning using git:// urls (necessary for
# submodules)
git config --global --add 'url.git://github.com/.insteadOf' 'git@github.com:'
git config --global --add 'url.git://github.com/.insteadOf' 'https://github.com/'
git clone --recursive --depth=1 git://github.com/LinePod/Raspberry.git ~/linepod

# Clone submodules of submodules
git submodule update --init --recursive --depth=1

cd ~/linespace
setup/setup.sh

# Reboot
reboot now
