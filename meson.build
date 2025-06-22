# Karere - Root meson.build file

project(
  'karere',
  'c', 'cpp', # C/C++ needed for gobject-introspection
  version: '0.6.4',
  meson_version: '>= 0.60.0',
  default_options: [
    'warning_level=1',
    'cpp_std=c++17'
  ],
)

# Process the frontend subdirectory
subdir('frontend')

# Install backend files
backend_files = [
  'backend/backend.js',
  'backend/logger.js',
  'backend/database.js',
  'backend/service-manager.js',
  'backend/package.json',
  'backend/package-lock.json'
]

install_data(
  backend_files,
  install_dir: get_option('datadir') / 'karere-backend'
)
