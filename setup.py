#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
from setuptools import find_packages, setup, Extension
from Cython.Distutils import build_ext
from scripts.version import get_git_version

ext_modules = [
    Extension("chaosc.c_osc_lib", ["chaosc/c_osc_lib.pyx"], extra_compile_args=["-O2", "-pipe", "-march=native"])
]

if sys.version_info >= (3,):
    extras['use_2to3'] = True


setup(
    name='chaosc',
    version=get_git_version(),
    packages=find_packages(exclude=["scripts",]),

    include_package_data = True,

    package_data = {
        "chaosc" :  ["config/*",]},

    exclude_package_data = {'': ['.gitignore']},

    install_requires=["Cython", "numpy"],

    # installing unzipped
    zip_safe = False,

    # predefined extension points, e.g. for plugins
    entry_points = """
    [console_scripts]
    chaosc = chaosc.chaosc:main
    chaosc_ctl = chaosc.chaosc_ctl:main
    chaosc_transcoder = chaosc.chaosc_transcoder:main
    chaosc_dump = chaosc.chaosc_dump:main
    chaosc_filter = chaosc.chaosc_filter:main
    chaosc_recorder = chaosc.chaosc_recorder:main
    chaosc_stats = chaosc.chaosc_stats:main
    """,
    # pypi metadata
    author = "Stefan Kögl",

    # FIXME: add author email
    author_email = "",
    description = "osc filtering application level gateway",

    # FIXME: add long_description
    long_description = """
    """,

    # FIXME: add license
    license = "GPL",

    # FIXME: add keywords
    keywords = "",

    # FIXME: add download url
    url = "",
    cmdclass = {'build_ext': build_ext},
    ext_modules = ext_modules,
    test_suite='tests'
)
