#!/usr/bin/env python
from setuptools import setup
from pathlib import Path

import os

repo_root = os.path.dirname(os.path.abspath(__file__))


with open("ranked/__init__.py") as file:
    for line in file.readlines():
        if 'version' in line:
            version = line.split('=')[1].strip().replace('"', "")
            break

args = dict(
    name="ranked",
    version="0.0.1",
    description="Player Ranking Algorithm benchmarks",
    long_description=(Path(__file__).parent / "README.rst").read_text(),
    author="Pierre Delaunay",
    author_email="pierre@delaunay.io",
    license='BSD-3-Clause',
    url="https://github.com/Delaunay/ranked",
    packages=[
        "ranked",
        "ranked.models",
        "ranked.datasets",
        "ranked.utils",
    ],
    zip_safe=True,
    python_requires='>=3.7.*',
    install_requires=[
        "scipy",
        "altair",
        "trueskill",
        "numpy",
        'orion',
        'typing_extensions',
    ],
    setup_requires=["setuptools"],
)

args["classifiers"] = [
    "Development Status :: 1 - Planning",
    "Intended Audience :: Developers",
    "Intended Audience :: Education",
    "Intended Audience :: Science/Research",
    "License :: OSI Approved :: BSD License",
    "Operating System :: POSIX",
    "Operating System :: Unix",
    "Programming Language :: Python",
    "Topic :: Scientific/Engineering",
    "Topic :: Scientific/Engineering :: Artificial Intelligence",
] + [("Programming Language :: Python :: %s" % x) for x in "3 3.7 3.8 3.9 3.10".split()]

if __name__ == "__main__":
    setup(**args)
