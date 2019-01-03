#!/usr/bin/env bash

which python

[ -d build ] && rm -rfv build
mkdir -v build
meson . build --prefix=$PWD/build/testdir
ninja -C build
ninja -C build install
ninja -C build run