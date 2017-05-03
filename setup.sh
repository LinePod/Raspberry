mkdir linespace
cd linespace

apt-get install python-pip -y
apt-get install python-dev -y
apt-get install libbluetooth-dev -y
apt-get install git -y
apt-get install expect -y

pip install pybluez
pip install pyusb
pip install pint

git clone https://github.com/vishnubob/silhouette.git
cd silhouette
pyton setup.py install
