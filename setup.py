#!/usr/bin/env python
import os
from setuptools import setup

from redilock import __version__, __author__, __author_email__, __url__
_README_FILE = os.path.join(os.path.dirname(__file__), "README.md")
setup(
    name="python-redilock",
    version=__version__,
    author=__author__,
    author_email=__author_email__,
    description="Simple Redis Distributed Lock",
    license="MIT",
    keywords="redis distributed lock mutex",
    packages=["redilock", "tests", ],
    #long_description=open(_README_FILE).read(),
    classifiers=[
        "Development Status :: 3 - Alpha",
    ],
    url=__url__
)
