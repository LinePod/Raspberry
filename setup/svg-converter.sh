#!/bin/bash
apt-get install -y libboost-dev libeigen3-dev libxml2-dev libspdlog-dev cmake -y

GIT_SSH_COMMAND="ssh -i $SSH_KEY_DIR/linespace-svg-simplifier" git clone --recursive --depth=1 git@github.com:Felerius/linespace-svg-simplifier.git svg-simplifier
cd svg-simplifier
mkdir build
cd build
cmake -DCMAKE_BUILD_TYPE=Release ..

# If on a raspberry pi, increase swap size
if [[ -z "${IS_PI+x}" ]]; then
    sed -i 's/^CONF_SWAPSIZE/#CONF_SWAPSIZE/' /etc/dphys-swapfile
    echo 'CONF_SWAPSIZE=2048' >> /etc/dphys-swapfile
    sudo /etc/init.d/dphys-swapfile restart
fi

make svg_converter

# Revert swapsize
if [[ -z "${IS_PI+x}" ]]; then
    sed -i '/^CONF_SWAPSIZE/d' /etc/dphys-swapfile
    sed -i 's/^#CONF_SWAPSIZE/CONF_SWAPSIZE/' /etc/dphys-swapfile
    sudo /etc/init.d/dphys-swapfile restart
fi

cd ../..
