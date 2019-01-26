project('gwe',
  version: run_command(
    'grep',
    'APP_VERSION',
    files('gwe/conf.py')
  ).stdout().split(' = ')[1].strip().strip('"'),
  meson_version: '>= 0.40.0'
)
# project version is defined in gwe/conf.py

# i18n = import('i18n')
python3 = import('python3')
python = import('python3')
prefix = get_option('prefix')
pkgdatadir = join_paths(prefix, get_option('datadir'), meson.project_name())
DATA_DIR = pkgdatadir
pythondir = join_paths(prefix, python.sysconfig_path('purelib'))
python_dir = pythondir

install_subdir('gwe', install_dir: pythondir)
subdir('data')
subdir('bin')

meson.add_install_script('scripts/meson_post_install.py')