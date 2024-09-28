#!/usr/bin/env python
import os
from setuptools import setup

_README_FILE = os.path.join(os.path.dirname(__file__), "README.md")
setup(
    name="python-redilock",
    version="0.0.4",
    author="Zvika Ferentz",
    description="Simple Redis Distributed Lock",
    license="MIT",
    keywords="redis distributed lock mutex",
    packages=["mean", "tests", "doc"],
    long_description=open(_README_FILE).read(),
    classifiers=[
        "Development Status :: 3 - Alpha",
    ],
)
