platinumshrimp
=================================================

[![Travis CI Build Status](https://travis-ci.com/Tigge/platinumshrimp.svg?branch=master)](https://travis-ci.com/Tigge/platinumshrimp)


Get the code:

 - git clone https://github.com/Tigge/platinumshrimp.git

Install dependencies in Debian/Ubuntu:

 - `sudo apt-get install python3-pip libzmq3-dev`
 - `sudo pip3 install requests requests-mock feedparser python-dateutil pyzmq irc`

Install dependencies in Fedora:

 - `sudo dnf install python3-devel python3-pip zeromq-devel`
 - `sudo pip-python3 install requests requests-mock feedparser python-dateutil pyzmq irc six`

Run plugins unit tests:

 - `python3 -m unittest discover -v`

Run:

 - `python3 bot.py`

Clean up:

 - ``rm -Rf `find . -name "*.pyc" -or -name __pycache__ -or -name _trial_temp -or -name "*.log" -or -name "ipc_plugin_*"` ``

