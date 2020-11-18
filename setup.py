from setuptools import setup, find_packages

setup(
    name="Platinumshrimp",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "requests>=2.20.0",
        "requests-mock>=1.5.2",
        "feedparser>=5.2.1",
        "python-dateutil>=2.7.5",
        "pyzmq>=17.0",
        "irc>=17.0",
    ],
    # metadata for upload to PyPI
    author="Platinumshrimp Developers",
    author_email="platinumshrimp@googlegroups.com",
    description="IRC Bot Framework",
    license="MIT",
    url="https://github.com/Tigge/platinumshrimp",
)
