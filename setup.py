#!/usr/bin/env python

"""The setup script."""

from setuptools import setup, find_packages

with open('README.rst') as readme_file:
    readme = readme_file.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = fh.read()

test_requirements = ['pytest>=3', ]

setup(
    author="Arran McCabe",
    author_email='arran@availabl.ai',
    python_requires='>=3.6',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],
    description="CLI for AWS CLoudWatch Alarm Tuning/Creation",
    entry_points={
        'console_scripts': [
            'cwtune=cwtune.cli:main',
        ],
    },
    install_requires=requirements,
    license="MIT license",
    long_description=readme,
    include_package_data=True,
    keywords='cwtune',
    name='cwtune',
    packages=find_packages(include=['cwtune', 'cwtune.*']),
    test_suite='tests',
    tests_require=test_requirements,
    url='https://github.com/availabl-co/cwtune',
    version='0.1.16',
    zip_safe=False,
)
