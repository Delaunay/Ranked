#!/usr/bin/env python
from setuptools import setup


if __name__ == '__main__':
    setup(
        name='ranked',
        version='0.0.0',
        description='Model Zoo for Ranking algo',
        author='Pierre Delaunay',
        packages=[
            'ranked',
        ],
        install_requires=['scipy', 'altair'],
        setup_requires=['setuptools'],
    )
