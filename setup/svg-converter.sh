#!/bin/bash
apt-get install -y libboost-dev libeigen3-dev libxml2-dev libspdlog-dev cmake -y

GIT_SSH_COMMAND="ssh -i $SSH_KEY_DIR/linespace-svg-simplifier" git clone --recursive --depth=1 git@github.com:Felerius/linespace-svg-simplifier.git svg-simplifier
cd svg-simplifier
mkdir build
cd build
cmake -DCMAKE_BUILD_TYPE=Release ..
make svg_converter

cd ../..
