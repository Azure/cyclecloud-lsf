#!/bin/bash -e
# if it already is installed, just exit
if [ -e ~/.010.finished ]; then
	exit 0;
fi;

printf "\ninstalling system packages\n\n"



yum install -y git swig pip gcc python-devel python-pip patch readline-devel

printf "\ninstalling virtualenv\n\n"
pip install virtualenv readline

rm -rf  ~/.virtualenvs/lsf

printf "\ncreating virtualenv\n\n"
virtualenv ~/.virtualenvs/lsf

source ~/.virtualenvs/lsf/bin/activate

cd ~
printf "\ncloning lsf-python-api\n\n"
rm -rf lsf-python-api
git clone https://github.com/IBMSpectrumComputing/lsf-python-api
cd lsf-python-api

printf "\nloading profile.lsf\n\n"

set +e
source /usr/share/lsf/conf/profile.lsf
set -e

echo Done loading profile.lsf

printf "\nbuilding lsf-python-api\n\n"
python setup.py build
printf "\ninstalling lsf-python-api\n\n"
python setup.py install

printf "\ntesting that the library can be loaded\n\n"
# reload the venv so the changes are picked up
source ~/.virtualenvs/lsf/bin/activate
# python -c 'from pythonlsf import lsf'
touch ~/.010.finished
printf "\nSuccess!\n"
