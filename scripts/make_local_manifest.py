#!/usr/bin/env python3
import subprocess
import sys
import json
from distutils.dir_util import copy_tree
from pathlib import Path

in_file = sys.argv[1]
git_repo = Path(__file__).parent.parent / '.git'
output = sys.argv[2]

copy_tree(str(Path(in_file).parent.absolute()), str(Path(output).parent.absolute()))
manifest = json.load(open(in_file, encoding='utf-8'))
manifest['modules'][0]['sources'][0]['url'] = str(git_repo)
manifest['modules'][0]['sources'][0]['commit'] = subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode('utf-8').strip()
manifest['modules'][0]['sources'][0].pop('branch', None)
manifest['modules'][0]['sources'][0].pop('tag', None)
json.dump(manifest, open(output, 'w', encoding='utf-8'))
