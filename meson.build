# karere-app/meson.build (Root meson file)

project(
  'karere',
  'c', 'cpp', # C/C++ needed for gobject-introspection
  version: '0.1.0',
  meson_version: '>= 0.60.0',
  default_options: [
    'warning_level=1',
    'cpp_std=c++17'
  ],
)

# Instruct Meson to look for the main project files in the frontend subdirectory
subdir('frontend')
```meson
# karere-app/frontend/meson.build (Frontend meson file)

project(
  'karere-frontend',
  'c',
  version: '0.1.0',
  meson_version: '>= 0.60.0',
)

i18n = import('i18n')
gnome = import('gnome')

python3 = find_program('python3', required: true)

# Set the application ID
application_id = 'io.github.tobagin.Karere'

# GSettings Schema
install_data(
  'data/io.github.tobagin.Karere.gschema.xml',
  install_dir: join_paths(get_option('datadir'), 'glib-2.0', 'schemas')
)

# Compile the GSettings schema
compile_schemas = custom_target(
  'gschemas.compile',
  input: 'data/io.github.tobagin.Karere.gschema.xml',
  output: 'gschemas.compiled',
  command: [find_program('glib-compile-schemas'), '--strict', '--targetdir', '@OUTPUT@', '@INPUT@'],
  install: true,
  install_dir: join_paths(get_option('datadir'), 'glib-2.0', 'schemas')
)

# UI files
gnome.compile_resources('karere-resources',
  'data/karere.gresource.xml',
  gresource_bundle: true,
  install: true,
  install_dir: get_option('pkgdatadir'),
  source_dir: 'data'
)

# Python module files
py_sources = [
  'karere/main.py',
  'karere/window.py',
  'karere/websocket_client.py',
]

install_data(
  py_sources,
  install_dir: join_paths(get_option('prefix'), get_option('pkgdatadir'), 'karere')
)

# Main executable script
executable_script = configure_file(
  input: 'karere.in',
  output: 'karere',
  configuration: {
    'pkgdatadir': join_paths(get_option('prefix'), get_option('pkgdatadir')),
    'pkglibdir': join_paths(get_option('prefix'), get_option('libdir')),
    'version': meson.project_version(),
    'application_id': application_id,
    'python': python3.path()
  },
  install: true,
  install_dir: get_option('bindir')
)

# Desktop file
i18n.merge_file(
  input: 'data/io.github.tobagin.Karere.desktop.in',
  output: 'io.github.tobagin.Karere.desktop',
  po_dir: 'po',
  type: 'desktop',
  install: true,
  install_dir: join_paths(get_option('datadir'), 'applications')
)

# AppData file
i18n.merge_file(
  input: 'data/io.github.tobagin.Karere.appdata.xml.in',
  output: 'io.github.tobagin.Karere.appdata.xml',
  po_dir: 'po',
  install: true,
  install_dir: join_paths(get_option('datadir'), 'metainfo')
)
