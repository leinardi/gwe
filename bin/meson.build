conf = configuration_data()
conf.set('VERSION', meson.project_version())
conf.set('localedir', join_paths(prefix, get_option('localedir')))
conf.set('PKGDATA_DIR', PKGDATA_DIR)
conf.set('PYTHON', python.find_python().path())
conf.set('PYTHON_DIR', join_paths(prefix, PYTHON_DIR))

configure_file(
  input: 'gwe.in',
  output: 'gwe',
  configuration: conf,
  install: true,
  install_dir: get_option('bindir')
)

configure_file(
  input: 'gwe-agent.in',
  output: 'gwe-agent',
  configuration: conf,
  install: true,
  install_dir: get_option('bindir')
)

gwe = join_paths(meson.build_root(), 'bin', 'gwe')
run_target('run',
  command: [gwe]
)
