#!/usr/bin/env bash

which python

[ -d build ] && rm -rfv build
find . -regex '^.*\(__pycache__\|\.py[co]\)$' -delete
mkdir -v build
meson . build --prefix=$PWD/build/testdir
ninja -C build
ninja -C build install
ninja -C build run