apt-get update -y
apt-get install python-pip -y
apt-get install python-dev -y
apt-get install libbluetooth-dev -y
apt-get install git -y
apt-get install expect -y

pip install pybluez
pip install pyusb
pip install pint

git clone https://github.com/boeckhoff/linespace_raspberry.git
cd linespace_raspberry

git clone https://github.com/vishnubob/silhouette.git
cd silhouette
python setup.py install
cd ..

apt-get install libboost-dev libeigen3-dev libxml2-dev cmake -y
git clone --recursive https://github.com/Felerius/linespace-svg-simplifier.git
cd linespace-svg-simplifier
mkdir build
cd build
cmake -DCMAKE_BUILD_TYPE=Release ..
make svg_converter
