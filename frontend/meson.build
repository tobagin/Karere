# frontend/meson.build

# Import required modules
i18n = import('i18n')
gnome = import('gnome')

python3 = find_program('python3', required: true)
application_id = 'io.github.tobagin.Karere'

# --- Define Installation Directories ---
pkgdatadir = join_paths(get_option('datadir'), meson.project_name())

# --- GSettings Schema ---
gnome.compile_schemas()

# --- Resources ---
gnome.compile_resources('karere-resources',
  'data/karere.gresource.xml',
  gresource_bundle: true,
  install: true,
  install_dir: pkgdatadir,
  source_dir: 'data'
)

# --- Python Sources ---
py_sources = [
  'karere/main.py',
  'karere/window.py',
  'karere/websocket_client.py',
  'karere/__init__.py',
]

install_data(
  py_sources,
  install_dir: join_paths(pkgdatadir, 'karere')
)

# --- Executable Script ---
# We pass the source directory path to the script template.
# This allows us to set PYTHONPATH correctly for development.
configure_file(
  input: 'karere.in',
  output: 'karere',
  configuration: {
    'pkgdatadir': pkgdatadir,
    'python': python3.full_path(),
    'source_dir': meson.current_source_dir()
  },
  install: true,
  install_dir: get_option('bindir'),
  install_mode: 'rwxr-xr-x'
)


# --- Desktop Integration ---
install_data(
  'data/io.github.tobagin.Karere.desktop.in',
  rename: application_id + '.desktop',
  install_dir: join_paths(get_option('datadir'), 'applications')
)

install_data(
  'data/io.github.tobagin.Karere.appdata.xml.in',
  rename: application_id + '.appdata.xml',
  install_dir: join_paths(get_option('datadir'), 'metainfo')
)
