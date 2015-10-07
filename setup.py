#!/usr/bin/env python

#from setuputils import setup
from distutils.core import setup

sctk = {
    "name": "silhouette",
    "description": "Python based silhouette framework",
    "author":"Giles Hall",
    "packages": ["silhouette"],
    "package_dir": {"silhouette": "src"},
    "py_modules":[
        "silhouette.__init__",
        "silhouette.gpgl",
        "silhouette.silhouette",
        "silhouette.utils",
    ],
    "version": "0.1",
    "install_requires": ['pyusb'],
    "extras_require": {
        'svg': ['pqdict', 'shapely', 'svg.path', 'kdtree', 'pint'],
    }
}

if __name__ == "__main__":
    setup(**sctk)
