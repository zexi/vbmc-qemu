#!/bin/bash

GIT_URL="https://git.coding.net/zexi/openipmi.git"
SRC_DIR="$(dirname $(dirname $(realpath $0)))"
WORKSPACE=$SRC_DIR/workspace

[ -d $WORKSPACE ] || mkdir -p $WORKSPACE

git clone "$GIT_URL" "$WORKSPACE/openipmi"
pushd "$WORKSPACE/openipmi"
git checkout origin/v2.0.22-lzx
make clean
autoreconf -ivf
./configure --prefix=/opt/openipmi --sysconfdir=/opt/openipmi/etc \
    --with-perlinstall=/opt/openipmi/usr/lib/perl \
    --with-pythoninstall=/opt/openipmi/usr/lib/python
make -j $(nproc)
sudo make install
popd
