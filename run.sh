#!/usr/bin/env bash

. build.sh && \
ninja -v -C ${MESON_BUILD_DIR} run
