# frontend/meson.build

# Import required modules
i18n = import('i18n')
gnome = import('gnome')

python3 = find_program('python3', required: true)
# Allow overriding application ID for development builds
application_id = get_option('app_id')

# --- Define Installation Directories ---
pkgdatadir = join_paths(get_option('datadir'), meson.project_name())

# --- GSettings Schema ---
gnome.compile_schemas()

# --- Resources ---
# Use development gresource if building for development app ID
gresource_file = application_id.endswith('.Devel') ? 'data/karere-devel.gresource.xml' : 'data/karere.gresource.xml'

gnome.compile_resources('karere-resources',
  gresource_file,
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
    'source_dir': meson.current_source_dir(),
    'app_id': application_id
  },
  install: true,
  install_dir: get_option('bindir'),
  install_mode: 'rwxr-xr-x'
)


# --- Desktop Integration ---
# Use development files if building for development app ID
desktop_file = application_id.endswith('.Devel') ? 'data/io.github.tobagin.Karere.Devel.desktop.in' : 'data/io.github.tobagin.Karere.desktop.in'
appdata_file = application_id.endswith('.Devel') ? 'data/io.github.tobagin.Karere.Devel.appdata.xml.in' : 'data/io.github.tobagin.Karere.appdata.xml.in'

install_data(
  desktop_file,
  rename: application_id + '.desktop',
  install_dir: join_paths(get_option('datadir'), 'applications')
)

# Skip appdata for development builds to avoid AppStream validation issues
if not application_id.endswith('.Devel')
  install_data(
    appdata_file,
    rename: application_id + '.appdata.xml',
    install_dir: join_paths(get_option('datadir'), 'metainfo')
  )
endif
