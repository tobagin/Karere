# Karere - Root meson.build file

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

# Process the frontend subdirectory
subdir('frontend')
