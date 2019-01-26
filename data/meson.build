gnome = import('gnome')

app_id = 'com.leinardi.gwe'

desktop_conf = configuration_data()
desktop_conf.set('bindir', join_paths(prefix, get_option('bindir')))

desktop_file = configure_file(
  input: app_id + '.desktop.in',
  output: app_id + '.desktop',
  #type: 'desktop',
  install: true,
  install_dir: join_paths(get_option('datadir'), 'applications'),
  configuration: desktop_conf
)

message('Looking for dependencies')
python_bin = python.find_python()
if not python_bin.found()
    error('No valid python3 binary found')
else
    message('Found python3 binary')
endif


# TODO: Requires GLib 2.52 because of Meson issue
#desktop_service = configure_file(
#  input: app_id + '.service.desktop.in',
#  output: app_id + '.service.desktop',
#  configuration: desktop_conf,
#  install: true,
#  install_dir: PKGDATA_DIR,
#)

# i18n.merge_file(
#   input: desktop_file,
#   output: app_id + '.desktop',
#   type: 'desktop',
#   po_dir: '../po',
#   install: true,
#   install_dir: join_paths(get_option('datadir'), 'applications')
# )
#
# i18n.merge_file(
#   input: app_id + '.appdata.xml.in',
#   output: app_id + '.appdata.xml',
#   po_dir: '../po',
#   install: true,
#   install_dir: join_paths(get_option('datadir'), 'appdata')
# )

dbus_conf = configuration_data()
dbus_conf.set('bindir', join_paths(prefix, get_option('bindir')))

configure_file(
  input: app_id + '.service.in',
  output: app_id + '.service',
  configuration: dbus_conf,
  install: true,
  install_dir: join_paths(get_option('datadir'), 'dbus-1/services')
)

install_data(app_id + '.gschema.xml',
  install_dir: join_paths(get_option('datadir'), 'glib-2.0/schemas')
)

if false
  gtk_encode_symbolic = find_program('gtk-encode-symbolic-svg')
  sizes = ['32x32', '64x64']
  icon_targets = []
  foreach size: sizes
    icon_targets += custom_target('symbolic-icon-' + size,
      input: 'icons/com.leinardi.gwe-symbolic.svg',
      output: 'icons/com.leinardi.gwe-symbolic.png',
      command: [gtk_encode_symbolic, '--output=' + meson.current_build_dir(), '@INPUT@', size]
    )
  endforeach
endif

icondir = join_paths(get_option('datadir'), 'icons/hicolor')
install_data('icons/com.leinardi.gwe.svg',
  install_dir: join_paths(icondir, 'scalable/apps')
)
install_data('icons/com.leinardi.gwe-symbolic.svg',
  install_dir: join_paths(icondir, 'symbolic/apps')
)

contributors = '\n'.join([
  'Roberto Leinardi (leinardi) &lt;roberto@leinardi.com&gt;',
  'Gabriele Musco (gabmus) &lt;emaildigabry@gmail.com&gt;'
])

LIBEXEC_DIR = join_paths(get_option('prefix'), get_option('libexecdir'))
EXTENSION_DIR = join_paths(get_option('prefix'), get_option('libdir'), meson.project_name())
bindir = join_paths(get_option('prefix'), get_option('bindir'))

glade_conf = configuration_data()
glade_conf.set('PACKAGE_URL', 'https://gitlab.com/leinardi/gwe')
glade_conf.set('DATA_DIR', DATA_DIR)
glade_conf.set('EXTENSION_DIR', EXTENSION_DIR)
glade_conf.set('LOCALE_DIR', join_paths(get_option('prefix'), get_option('datadir'), 'locale'))
glade_conf.set('PYTHON_DIR', PYTHON_DIR)
glade_conf.set('PYTHON_EXEC_DIR', join_paths(get_option('prefix'), python.sysconfig_path('stdlib')))
glade_conf.set('PYTHON', python_bin.path())
glade_conf.set('APPID', app_id)
glade_conf.set('libexecdir', LIBEXEC_DIR)
# this is for development version # glade_conf.set('VERSION', ''.join([run_command(['git', 'describe', '--long', '--tags']).stdout(), get_option('profile')]))
glade_conf.set('VERSION', meson.project_version())
glade_conf.set('CONTRIBUTORS', contributors)

gwe_resources = gnome.compile_resources(app_id,
  app_id + '.gresource.xml',
  gresource_bundle: true,
  install: true,
  install_dir: PKGDATA_DIR
)

#gwe_resources = gnome.compile_resources(app_id,
#  app_id + '.gresource.xml',
#  gresource_bundle: true,
#  dependencies: configure_file (
#    input: 'ui/aboutdialog.glade.in',
#    output: 'aboutdialog.glade',
#    configuration: glade_conf
#  ),
#  install: true,
#  install_dir: PKGDATA_DIR
#)

gwe_settings = gnome.compile_schemas()

install_data(
  app_id + '.appdata.xml',
  install_dir: join_paths(get_option('datadir'), 'metainfo')
)
