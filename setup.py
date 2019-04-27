

from setuptools import setup, find_packages, find_namespace_packages
from cerberus import (
    __version__,
    __author__,
    __email__,
    __url__,
    __description__
)
setup(
    name='cerberus',
    author=__author__,
    author_email=__email__,
    description=__description__,
    url=__url__,
    version=__version__,
    install_requires=[
        'click', 
        'click-configfile', 
        'click-alias',
        'pyvmomi', 
        'dnspython', 
        'requests'
    ],
    include_package_data=True,
    packages=find_packages(),
    entry_points='''
        [console_scripts]
        cerberus=cerberus.scripts.cli:cli
    ''',
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)