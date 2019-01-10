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

if get_option('with-flatpak')
  # We keep a generic manifest in the repo you can use but
  # we want builds to use the local files so simply rewrite it
  make_local_manifest = find_program('scripts/make_local_manifest.py')
  local_manifest = custom_target('manifest',
    input: 'dist/flatpak/com.leinardi.gwe.json',
    output: 'com.leinardi.gwe.json',
    command: [make_local_manifest, '@INPUT@', '@OUTPUT@']
  )

  # Build a bundle for both testing and releases
  build_flatpak = find_program('scripts/build_flatpak.py')
  custom_target('flatpak',
    input: local_manifest,
    output: 'com.leinardi.gwe.flatpak',
    command: [build_flatpak, '@INPUT@', '@OUTPUT@'],
    build_always: true
    # TODO: This shouldn't build unless explicit
  )
endif
