#!/usr/bin/env python3
from distutils.core import setup
import subprocess
import os
import sys
import importlib.resources

with importlib.resources.path('srht', 'Makefile') as f:
    srht_path = f.parent.as_posix()

make = os.environ.get("MAKE", "make")
subp = subprocess.run([make, "SRHT_PATH=" + srht_path])
if subp.returncode != 0:
    sys.exit(subp.returncode)

ver = os.environ.get("PKGVER") or subprocess.run(['git', 'describe', '--tags'],
      stdout=subprocess.PIPE).stdout.decode().strip()

setup(
  name = 'todosrht',
  packages = [
      'todosrht',
      'todosrht.types',
      'todosrht.blueprints',
      'todosrht.blueprints.api',
      'todosrht.alembic',
      'todosrht.alembic.versions'
  ],
  version = ver,
  description = 'todo.sr.ht website',
  author = 'Drew DeVault',
  author_email = 'sir@cmpwn.com',
  url = 'https://todo.sr.ht/~sircmpwn/todo.sr.ht',
  install_requires = [
    'pystache',
    'srht',
  ],
  license = 'AGPL-3.0',
  package_data={
      'todosrht': [
          'templates/*.html',
          'templates/*.js',
          'static/*',
          'static/icons/*',
          'emails/*'
          'schema.graphqls',
          'default_query.graphql'
      ]
  },
  scripts = [
      'todosrht-initdb',
      'todosrht-lmtp',
      'todosrht-migrate',
  ]
)
