#!/bin/sh
set -ex

if [ "$INSIDE_DOCKER" = "1" ]; then
  MACH="docker"
else
  MACH="host"
fi
VENV_NAME=".venv-$(uname -m)-${MACH}"

if [ ! -d "${VENV_NAME}" ]; then
  python3 -m venv "${VENV_NAME}"
fi
./${VENV_NAME}/bin/pip3 install -r requirements.txt
./${VENV_NAME}/bin/python3 campaign_test.py
