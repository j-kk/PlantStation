from pkg_resources import VersionConflict, require
from setuptools import setup
from setuptools_scm import get_version

try:
    require('setuptools>=38.3')
except VersionConflict:
    print("Error: version of setuptools is too old (<38.3)!")
    exit(1)


if __name__ == "__main__":
    setup()
