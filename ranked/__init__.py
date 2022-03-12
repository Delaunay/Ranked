"""Top level module for ranked"""

__descr__ = "Model Zoo for Ranking algo"
__version__ = "version"
__license__ = "BSD 3-Clause License"
__author__ = u"Pierre Delaunay"
__author_email__ = "pierre@delaunay.io"
__copyright__ = u"2022 Pierre Delaunay"
__url__ = "https://github.com/Delaunay/Ranked"


def my_function(lhs: int, rhs: int) -> int:
    """Add two numbers together

    Parameters
    ----------
    lhs: int
        first integer

    rhs: int
        second integer

    Raises
    ------
    value errror if lhs == 0

    Examples
    --------

    >>> my_function(1, 2)
    3
    >>> my_function(0, 2)
    Traceback (most recent call last):
      ...
    ValueError

    """
    if lhs == 0:
        raise ValueError()

    return lhs + rhs
