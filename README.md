platinumshrimp
=================================================

[![Travis CI Build Status](https://travis-ci.org/Tigge/platinumshrimp.svg?branch=master)](https://travis-ci.org/Tigge/platinumshrimp)


Get the code:

 - `git clone https://github.com/Tigge/platinumshrimp.git`

Install dependencies in Debian/Ubuntu:

 - `sudo apt-get install python3-pip libzmq3-dev`
 - `sudo ./setup.py develop`

Install dependencies in Fedora:

 - `sudo dnf install python3-devel python3-pip zeromq-devel`
 - `sudo ./setup.py develop`

Run plugins unit tests:

 - `./setup.py tests`

Run:

 - `platinumshrimp`

Clean up:

 - ```rm -Rf `find . -name "*.pyc" -or -name __pycache__ -or -name "*.log"` ```

