from setuptools import setup, find_packages
setup(
    name = "Platinumshrimp",
    version = "0.1",
    packages = find_packages(),
    scripts = ['say_hello.py'],

    install_requires = [
        'requests>=2.7.0',
        'requests-mock>=0.7.0',
        'feedparser>=5.2.1',
        'python-dateutil>=2.4.2',
        'pyzmq>=14.0',
        'irc>=13.0'],

    package_data = {
        # If any package contains *.txt or *.rst files, include them:
        '': ['*.txt', '*.rst'],
        # And include any *.msg files found in the 'hello' package, too:
        'hello': ['*.msg'],
    },

    # metadata for upload to PyPI
    author = "Platinumshrimp Developers",
    author_email = "platinumshrimp@googlegroups.com",

    description = "This is an Example Package",
    license = "PSF",
    keywords = "hello world example examples",
    url = "https://github.com/Tigge/platinumshrimp",
)