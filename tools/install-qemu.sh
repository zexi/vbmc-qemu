#!/bin/bash

GIT_URL="https://git.coding.net/zexi/qemu.git"
SRC_DIR="$(dirname $(dirname $(realpath $0)))"
WORKSPACE=$SRC_DIR/workspace

[ -d $WORKSPACE ] || mkdir -p $WORKSPACE

git clone "$GIT_URL" "$WORKSPACE/qemu"
pushd "$WORKSPACE/qemu"
git checkout v2.7.0-rc5
git submodule update --init dtc
./configure --prefix=/opt/qemu2.7
make -j $(nproc)
sudo make install
popd
