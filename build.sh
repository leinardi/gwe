#!/usr/bin/env bash

MESON_BUILD_DIR="build/meson"
OUTPUT_DIR="build/output"
INSTALL_DIR="${OUTPUT_DIR}/install"

[[ -d ${MESON_BUILD_DIR} ]] && rm -rfv ${MESON_BUILD_DIR}
find . -regex '^.*\(__pycache__\|\.py[co]\)$' -delete
mkdir -pv ${MESON_BUILD_DIR} ${INSTALL_DIR}
meson . ${MESON_BUILD_DIR} --prefix=$PWD/${INSTALL_DIR} $@
ninja -v -C ${MESON_BUILD_DIR}
ninja -v -C ${MESON_BUILD_DIR} install