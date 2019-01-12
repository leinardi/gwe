#!/usr/bin/env python3
import subprocess
import sys
import json
from distutils.dir_util import copy_tree
from pathlib import Path

IN_FILE = sys.argv[1]
GIT_REPO = Path().cwd() / '.git'
OUTPUT = sys.argv[2]

copy_tree(str(Path(IN_FILE).parent.absolute()), str(Path(OUTPUT).parent.absolute()))
MANIFEST = json.load(open(IN_FILE, encoding='utf-8'))
MODULE = MANIFEST['modules'][-1]['sources'][0]
MODULE['url'] = str(GIT_REPO)
MODULE['commit'] = subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode('utf-8').strip()
MODULE.pop('branch', None)
MODULE.pop('tag', None)
json.dump(MANIFEST, open(OUTPUT, 'w', encoding='utf-8'))
