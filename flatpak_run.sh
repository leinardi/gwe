#!/usr/bin/env bash


flatpak uninstall com.leinardi.gwe -y
./build.sh -fl -fb -fi
flatpak run com.leinardi.gwe --debug
