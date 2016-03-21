#!/usr/bin/env python3
import os
import sys
import unittest

import ez_setup
ez_setup.use_setuptools()

from setuptools import setup, find_packages, Command


class Test(Command):
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run_folder(self, folder):
        print("Running test for " + folder)

        loader = unittest.TestLoader()
        suit = loader.discover(folder, top_level_dir=folder)

        runner = unittest.TextTestRunner()
        result = runner.run(suit)

        # TODO: Here be dragons
        if "test" in sys.modules:
            del sys.modules["test"]

        return result.wasSuccessful()

    def run(self):
        passed = True
        for folder in os.listdir(path="plugins"):
            passed = passed and self.run_folder("plugins/" + folder)
        passed = passed and self.run_folder("platinumshrimp")
        raise SystemExit(0 if passed else 1)


setup(
    name="platinumshrimp",
    version="0.1",
    packages=find_packages(),

    cmdclass={
        "test": Test
    },

    entry_points={
        "console_scripts": [
            "platinumshrimp = platinumshrimp.bot:run",
        ]
    },

    setup_requires=[
        "setuptools_git>=1.1"
    ],
    install_requires=[
        'requests>=2.7.0',
        'feedparser>=5.2.1',
        'python-dateutil>=2.4.2',
        'pyzmq>=14.0',
        'irc>=13.0'
    ],
    tests_require=[
        'requests-mock>=0.7.0',
    ],

    include_package_data=True,
    exclude_package_data={"": [".gitignore"]},

    author="Platinumshrimp Developers",
    author_email="platinumshrimp@googlegroups.com",

    description="IRC bot, with multiprocess multilanguage plugin support, written in Python 3.",
    license="MIT",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Environment :: Plugins",
        "Intended Audience :: End Users/Desktop",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Topic :: Communications :: Chat :: Internet Relay Chat",
        "Programming Language :: Python :: 3 :: Only"
    ],
    keywords="irc bot plugins",
    url="https://github.com/Tigge/platinumshrimp",
)
