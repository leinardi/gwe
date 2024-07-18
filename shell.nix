{ pkgs ? import <nixpkgs> { config.allowUnfree = true; } }:
let
  mach-nix = import (builtins.fetchGit {
    url = "https://github.com/DavHau/mach-nix";
    ref = "refs/tags/3.5.0";
  }) {
    mkPython = {  # replace with mkPythonShell if shell is wanted
      requirements = builtins.readFile ./requirements.txt;
    };
  };
  unstable = import (builtins.fetchTarball "https://github.com/NixOS/nixpkgs/archive/nixos-unstable.tar.gz") {};
in
pkgs.mkShell {
  packages = with pkgs; [
    (python3.withPackages (pypkgs: with pypkgs; [
      injector
      matplotlib
      packaging
      peewee
      pynvml
      pygobject3
      xlib
      pyxdg
      requests
      rx
      gtk3
      reactivex
      py3nvml
      ]))
    glib
    libgee
    #pantheon
#     lib
    wrapGAppsHook
    pkg-config
    meson
    ninja
    cmake
    gobject-introspection
    desktop-file-utils
    gtk3
    libdazzle
    libnotify
    # needed it because I use the unstable kernel in my configuration.nix
    unstable.linuxPackages.nvidia_x11
    #linuxPackages.nvidia_x11
    appstream-glib
    appstream
    flatpak-builder
    libayatana-appindicator
  ];

  shellHook = ''
    # Fix missing site-packages like gi
    site_packages=$(python3 -c "import site; print(site.getsitepackages()[0])")
    export PYTHONPATH="$site_packages"

    # Ensure NVML library is in LD_LIBRARY_PATH
    export LD_LIBRARY_PATH=${unstable.linuxPackages.nvidia_x11}/lib:$LD_LIBRARY_PATH
  '';
}
#   prePatch = ''
#     patchShebangs scripts/{make_local_manifest,meson_post_install}.py
#
#     substituteInPlace gwe/repository/nvidia_repository.py \
#       --replace "from py3nvml import py3nvml" "import pynvml" \
#       --replace "py3nvml.py3nvml" "pynvml" \
#       --replace "py3nvml" "pynvml"
#   '';
