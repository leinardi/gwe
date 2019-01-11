#!/usr/bin/env bash

MESON_BUILD_DIR="build/meson"
OUTPUT_DIR="build/output"
INSTALL_DIR="${OUTPUT_DIR}/install"

[[ -d ${OUTPUT_DIR} ]] && rm -rfv ${OUTPUT_DIR}
# keep .flatpak-builder
find ${MESON_BUILD_DIR}/* ${MESON_BUILD_DIR}/.[^.]* -maxdepth 0 -not -name '.flatpak-builder' -exec rm -rv {} +
find . -regex '^.*\(__pycache__\|\.py[co]\)$' -delete
mkdir -pv ${MESON_BUILD_DIR} ${INSTALL_DIR}
meson . ${MESON_BUILD_DIR} --prefix=$PWD/${INSTALL_DIR} $@
ninja -v -C ${MESON_BUILD_DIR}
ninja -v -C ${MESON_BUILD_DIR} install
