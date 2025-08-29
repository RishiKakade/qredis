# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

Project: QRedis — a Python/Qt GUI client for Redis.

Common commands
- Create a virtualenv and install in editable mode (recommended for development)
  - python3 -m venv .venv
  - source .venv/bin/activate
  - pip install -e .

- Run the app (no install required)
  - From source: python -m qredis [--host HOST] [-p PORT] [-s SOCK] [-n DB] [--name NAME] [-f FILTER] [--key-split CHARS] [--log-level LEVEL]
  - After install: qredis [same args]
  - Examples:
    - qredis -p 6379
    - qredis -s /tmp/redis.sock -n 5
    - qredis --log-level DEBUG

- Lint/format
  - Black (formatter): black .
  - Flake8 (linter): flake8
    - Configured via setup.cfg (max line length 88, ignore E203, exclude docs)
  - Pre-commit (runs black, flake8, and other hooks)
    - pip install pre-commit
    - pre-commit install
    - pre-commit run --all-files
    - Note: a giticket hook formats commit messages that include an 8+ digit ticket number to the form: "[{ticket}]: {commit_msg}".

- Build/distribute
  - Modern (requires `build`):
    - python -m pip install --upgrade build
    - python -m build
  - Legacy fallback:
    - python setup.py sdist bdist_wheel
  - Local install of built wheel:
    - pip install dist/*.whl

- Versioning
  - Configured with bumpversion in setup.cfg
  - Typical usage:
    - pip install bump2version  # provides the `bumpversion` CLI
    - bumpversion patch  (or: bumpversion minor | bumpversion major)

- Tests
  - No tests are present in this repository as of now.

High-level architecture
- Entrypoints
  - Console script: qredis -> qredis.window:main (declared in setup.py entry_points)
  - Module entry: python -m qredis runs qredis/__main__.py which calls window.main()

- UI composition
  - qredis.window.RedisWindow (QMainWindow)
    - Hosts a QMdiArea and menu/actions (open DB, restart, quit, about)
    - "Open DB" triggers qredis.dialog.OpenRedisDialog to create a QRedis connection and adds a new RedisPanel subwindow
    - Supports switching between TabbedView and SubWindowView modes
  - qredis.panel.RedisPanel (QSplitter)
    - Left: qredis.tree.RedisTree (tree of Redis keys)
    - Right: qredis.editor.RedisEditor (inspector/editor area)
    - Selection in the tree drives what the editor displays

- Data/model layer
  - qredis.redis.QRedis wraps redis.Redis, adding:
    - Typed getters for key types: string, hash, list, set, zset, stream
    - Heuristic value decoding (utf-8, pickle, msgpack) via DECODES
    - Qt signals for key rename and delete (keyRenamed, keysDeleted)
  - qredis.tree builds a navigable tree of keys
    - Node/RedisNode in-memory tree representation
    - RedisKeyModel (QAbstractItemModel) exposes keys to Qt views with icons and filtering

- Editors and DB inspector
  - qredis.editor.RedisEditor switches among:
    - RedisItemEditor for key values
      - SimpleEditor for string values (with increment helpers)
      - MultiEditor for lists/sets/hashes (table-based editing)
      - StreamViewer for Redis streams (read-only list + table view)
      - TTL and key rename operations are supported
    - RedisDbEditor for server info/config/clients with inline config editing

- Utilities and resources
  - qredis.qutil provides ui_loadable decorator and load_ui loader
    - .ui files (Qt Designer) are loaded from the qredis/ui/ directory
  - qredis.util defines KeyItem records, tooltips, restart helpers, and Redis connection string helpers
  - Package data includes images (qredis/images/*.png) and UI definitions (qredis/ui/*.ui) via setup.py

Runtime requirements (from setup.py)
- Python >= 3.5
- Dependencies: redis, qtpy, PyQt5, msgpack, msgpack-numpy
- A running Redis instance to connect to (via TCP host/port or Unix socket)

