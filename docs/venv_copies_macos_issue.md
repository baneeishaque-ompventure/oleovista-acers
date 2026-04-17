<!--
title: Python Venv Copies Flag macOS Issue
description: Troubleshooting documentation for the SIGABRT crash caused by the --copies flag when creating
Python virtual environments on macOS.
category: Environment Configuration
-->

# Python Venv Copies Flag macOS Issue

## Overview

When creating a Python virtual environment on macOS using Homebrew or pyenv distributions, using the `--copies`
flag with the `venv` module can lead to a `SIGABRT` crash during initialization.

## Symptoms

The environment creation fails during the `ensurepip` phase with an error similar to the following:

```text
dyld[94721]: Library not loaded: @executable_path/../lib/libpython3.11.dylib
  Referenced from: <4C4C44FC-5555-3144-A147-66A8723806F2> /Users/dk/lab-data/acers-backend/.venv/bin/python
  Reason: tried: '/Users/dk/lab-data/acers-backend/.venv/lib/libpython3.11.dylib' (no such file)
Error: Command '['/Users/dk/lab-data/acers-backend/.venv/bin/python', '-m', 'ensurepip', '--upgrade']' died
```

## Root Cause

On macOS, standard distributions of Python (like Homebrew or pyenv) compile the interpreter to be dynamically linked
against `libpython3.11.dylib`. When the `--copies` flag is used, the `python` executable is physically copied into the
`.venv/bin/` directory.

However, the `venv` module does not copy the corresponding dynamic library into the `.venv/lib/` directory.
Because the copied binary's `rpath` relies on `@executable_path/../lib/libpython3.11.dylib`, the executable crashes
immediately upon invocation due to the missing shared library.

## Resolution

Do not use the `--copies` flag when creating virtual environments on macOS with these Python distributions. Instead,
rely on the default symlink behavior, which correctly resolves the path back to the original dynamic library.

**Correct Command:**

```bash
python -m venv --upgrade-deps --clear .venv
```
