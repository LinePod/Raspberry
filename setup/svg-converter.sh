#!/bin/bash
apt-get install -y libboost-dev libeigen3-dev libxml2-dev libspdlog-dev cmake -y

cd svg-converter
mkdir build
cd build
cmake -DCMAKE_BUILD_TYPE=Release ..

# If on a raspberry pi, increase swap size
if [[ "$IS_PI" == 'true' ]]; then
    sed -i 's/^CONF_SWAPSIZE/#CONF_SWAPSIZE/' /etc/dphys-swapfile
    echo 'CONF_SWAPSIZE=2048' >> /etc/dphys-swapfile
    /etc/init.d/dphys-swapfile restart
fi

make svg_converter

# Revert swapsize
if [[ "$IS_PI" == 'true' ]]; then
    sed -i '/^CONF_SWAPSIZE/d' /etc/dphys-swapfile
    sed -i 's/^#CONF_SWAPSIZE/CONF_SWAPSIZE/' /etc/dphys-swapfile
    /etc/init.d/dphys-swapfile restart
fi

cd ../..
