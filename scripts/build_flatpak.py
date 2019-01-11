#!/usr/bin/env python3

import sys
import subprocess
from os import path
from pathlib import Path

flatpak_build_path = Path(__file__).parent.parent / 'build' / 'flatpak'
manifest = sys.argv[1]
output_file = flatpak_build_path.parent / 'output' / sys.argv[2]
app_id = path.basename(manifest).rpartition('.')[0]

repo_path = flatpak_build_path / 'repo'
build_path = flatpak_build_path / 'build'

repo_path.mkdir(parents=True, exist_ok=True)
build_path.mkdir(parents=True, exist_ok=True)
output_file.parent.mkdir(parents=True, exist_ok=True)

print(str(build_path))
print(str(manifest))
print(str(repo_path))

subprocess.call(
    ['flatpak-builder',
     '--force-clean',
     '--install-deps-from=flathub',
     str(build_path), str(manifest),
     '--repo=' + str(repo_path)
     ])
subprocess.call(['flatpak', 'build-bundle', str(repo_path), str(output_file), app_id])
