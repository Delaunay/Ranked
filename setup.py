#!/usr/bin/env python
from setuptools import setup


args = dict(
    name="ranked",
    version="0.0.0",
    description="Player Ranking Algorithm benchmarks",
    author="Pierre Delaunay",
    packages=[
        "ranked",
        "ranked.models",
        "ranked.datasets",
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
