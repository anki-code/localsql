#!/usr/bin/env python

import setuptools
from localsql import __version__

try:
    with open('README.md', 'r', encoding='utf-8') as fh:
        long_description = fh.read()
except (IOError, OSError):
    long_description = ''

setuptools.setup(
    name='localsql',
    version=__version__,
    license='BSD',
    author='localsql',
    author_email='author@example.com',
    description="Querying local files using SQL",
    long_description=long_description,
    long_description_content_type='text/markdown',
    python_requires='>=3.6',
    install_requires=['pandas', 'pandasql', 'openpyxl', 'prompt_toolkit', 'pygments', 'tableprint', 'argcomplete'],
    scripts=['localsql/localsql'],
    packages=setuptools.find_packages(),
    package_data={'localsql': ['*.py']},
    platforms='any',
    url='https://github.com/localsql/localsql',
    project_urls={
        "Documentation": "https://github.com/localsql/localsql/blob/master/README.md",
        "Code": "https://github.com/localsql/localsql",
        "Issue tracker": "https://github.com/localsql/localsql/issues",
    },
    classifiers=[
        "License :: OSI Approved :: BSD License"
    ]
)
