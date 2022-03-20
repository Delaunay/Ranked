#!/usr/bin/env python
from setuptools import setup

import os

repo_root = os.path.dirname(os.path.abspath(__file__))


args = dict(
    name="ranked",
    version="0.0.1",
    description="Player Ranking Algorithm benchmarks",
    long_description=open(
        os.path.join(repo_root, "README.rst"), "rt", encoding="utf8"
    ).read(),
    author="Pierre Delaunay",
    author_email="pierre@delaunay.io",
    url="https://github.com/Delaunay/Ranked",
    packages=[
        "ranked",
        "ranked.models",
        "ranked.datasets",
        "ranked.utils",
    ],
    install_requires=[
        "scipy",
        "altair",
        "trueskill",
        "numpy",
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
