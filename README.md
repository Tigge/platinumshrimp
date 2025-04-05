platinumshrimp
=================================================

[![Build status](https://github.com/Tigge/platinumshrimp/workflows/Build/badge.svg)](https://github.com/Tigge/platinumshrimp/actions?query=workflow%3ABuild)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Packaging: poetry](https://img.shields.io/badge/packaging-poetry-%23299BD7)](https://python-poetry.org/)


Get the code:

 - `git clone https://github.com/Tigge/platinumshrimp.git`

Install dependencies in Debian/Ubuntu:

 - `sudo apt-get install python3-pip libzmq3-dev`

Install dependencies in Fedora:

 - `sudo dnf install python3-devel python3-pip zeromq-devel`

Install poetry:

 - `curl -sSL https://install.python-poetry.org/ | python -`
 - `poetry update`

Run plugins unit tests:

 - `poetry run python -m unittest discover -v`

Run:

 - `poetry run python bot.py`

Clean up:

 - ``rm -Rf `find . -name "*.pyc" -or -name __pycache__ -or -name _trial_temp -or -name "*.log" -or -name "ipc_plugin_*"` ``

