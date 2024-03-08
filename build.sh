#!/bin/bash

BUILD_DIR="build"
OUTPUT_DIR="${BUILD_DIR}/output"
MESON_BUILD_DIR="${BUILD_DIR}/meson"
INSTALL_DIR="${OUTPUT_DIR}/install"

appstream-util validate-relax data/com.leinardi.gwe.appdata.xml || exit $?
appstream-util appdata-to-news data/com.leinardi.gwe.appdata.xml | sed '/^~*$/s/~/=/g' > CHANGELOG.md
[[ -d ${OUTPUT_DIR} ]] && rm -rfv ${OUTPUT_DIR}
find . -regex '^.*\(__pycache__\|\.py[co]\)$' -delete

[[ -d ${MESON_BUILD_DIR} ]] && rm -rfv ${MESON_BUILD_DIR}
mkdir -pv ${MESON_BUILD_DIR} ${INSTALL_DIR} && \
meson . ${MESON_BUILD_DIR} --prefix=$PWD/${INSTALL_DIR} && \
ninja -v -C ${MESON_BUILD_DIR} && \
desktop-file-validate build/meson/data/com.leinardi.gwe.desktop && \
ninja -v -C ${MESON_BUILD_DIR} install
