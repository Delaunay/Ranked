ranked
======

|pypi| |py_versions| |license|
|rtfd| |codecov| |style| |tests|

.. |pypi| image:: https://img.shields.io/pypi/v/ranked.svg
    :target: https://pypi.python.org/pypi/ranked
    :alt: Current PyPi Version

.. |py_versions| image:: https://img.shields.io/pypi/pyversions/ranked.svg
    :target: https://pypi.python.org/pypi/ranked
    :alt: Supported Python Versions

.. |license| image:: https://img.shields.io/badge/License-BSD%203--Clause-blue.svg
    :target: https://opensource.org/licenses/BSD-3-Clause
    :alt: BSD 3-clause license

.. |rtfd| image:: https://readthedocs.org/projects/ranked/badge/?version=stable
    :target: https://orion.readthedocs.io/en/stable/?badge=stable
    :alt: Documentation Status

.. |codecov| image:: https://codecov.io/gh/Delaunay/ranked/branch/master/graph/badge.svg
    :target: https://codecov.io/gh/Delaunay/ranked
    :alt: Codecov Report

.. |style| image:: https://github.com/Delaunay/Ranked/actions/workflows/style.yml/badge.svg
    :target: https://github.com/Delaunay/Ranked/actions/workflows/style.yml
    :alt: Github actions tests

.. |tests| image:: https://github.com/Delaunay/Ranked/actions/workflows/test.yml/badge.svg
    :target: https://github.com/Delaunay/Ranked/actions/workflows/test.yml
    :alt: Github actions tests



Features
~~~~~~~~

* A common interface for ranking algorithms
* Elo (Chess & Generic)
* Glicko2
* NoSkill (similar to Trueskill, i.e bayesian inference on a bipartite graph)
* Synthetics benchmarks
* Basic match maker
* Matchup replay to calibrate and experiment on real data
* Model calibration using black-box optimizer Orion


.. note::

   For team based games; When benchmarking ranking algorithm against real data you have
   to keep in mind that the matchmaking algorithm that created the groups
   was based on its own external ranking system so any measure
   that would come out of such benchmarks would end up being biased.

.. note::

   Similarly, matchmaking or the team building algorithm can impact the performance
   of the ranking algorithm. It is up to the matchmaking algorithm to make sure
   the teams it builds are as fair as possible.

   The ranking algorithm only provide an estimate of each player'skill to help
   the matchmaker to make the best decision possible.


WIP
---

* NoSkill2
* Dota2 extracted matches
* publish to Pypi


.. code-block:: bash

   pip install ranked


.. image:: https://github.com/Delaunay/Ranked/blob/master/docs/_static/example.png?raw=true