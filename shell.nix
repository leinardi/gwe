{ pkgs ? import <nixpkgs> { config.allowUnfree = true; }, ... }:
let
  lib = pkgs.lib;
  # Read the requirements.txt file
  requirements = builtins.readFile ./requirements.txt;
  sha_file = builtins.readFile ./nix_python_req_sha256.txt;

  # Split the requirements into lines and filter out empty lines
  lines = builtins.filter (line: builtins.isString line) (builtins.filter (line: line != "") (builtins.split "\n" requirements));
  shas = builtins.filter (line: builtins.isString line) (builtins.filter (sha: sha != "") (builtins.split "\n" sha_file));

  # Convert each requirement into a list of attributes with name and version
  parsedPackages = builtins.genList (idx: let
    parts = builtins.split "==" (builtins.elemAt lines idx);
    pname = builtins.head parts;
    version = builtins.tail (builtins.tail parts);
    sha256 = builtins.elemAt shas idx;
  in {
    pname = pname;
    version = builtins.head version;
    sha256 = sha256;
  }) (builtins.length lines);

  parsedPackages2 = builtins.filter (pkg: pkg.pname != "nvidia-ml-py") parsedPackages;

  # Fetch each package from PyPI
  fetchPkg = pkg: pkgs.fetchPypi {
    pname = "${pkg.pname}";
    version = pkg.version;
    sha256 = pkg.sha256;
  };

  unstable = import (builtins.fetchTarball "https://github.com/NixOS/nixpkgs/archive/nixos-unstable.tar.gz") {};
in
pkgs.mkShell {
  packages = with pkgs; [
    (python311.withPackages(pypkg:
      lib.lists.forEach parsedPackages (x: let
        pname = if (x.pname == "PyGObject") then
          "pygobject3"
        else if (x.pname == "python-xlib") then
          "xlib"
        else
          x.pname;
      in
        if pname == "nvidia-ml-py" then
          pypkg."${pname}".overrideAttrs (oldAttrs: {
            version = x.version;
            # sha256-6efxLvHsI0uw3CLSvcdi/6+rOUvcRyoHpDd8lbv5Ov4=
            src = (fetchPkg x);
          })
        else
          pypkg."${pname}".overrideAttrs (oldAttrs: {
            version = x.version;
          }
      )
    )
    ))
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
    linuxPackages.nvidia_x11_beta
    #linuxPackages.nvidia_x11
    appstream-glib
    flatpak-builder
    libayatana-appindicator
  ];

  shellHook = ''
  # Fix missing site-packages
  site_packages=$(python3 -c "import site; print(':'.join(site.getsitepackages()))")
  export PYTHONPATH="$site_packages:$PYTHONPATH"
  export PYTHON=${pkgs.python311}/bin/python

  # Ensure NVML library is in LD_LIBRARY_PATH
  export LD_LIBRARY_PATH=${pkgs.linuxPackages.nvidia_x11_beta}/lib:$LD_LIBRARY_PATH
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

