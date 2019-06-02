"""Setuptools installation script for paperpile-tools package."""

from setuptools import setup
import re


# Get contents of README file
with open('README.md') as fh:
	readme_contents = fh.read()


# Read version from root module __init__.py
with open('paperpile_tools/__init__.py') as fh:
	init_contents = fh.read()
	version_match = re.search('^__version__ = ["\']([^"\']+)["\']', init_contents, re.M)

	if not version_match:
		raise RuntimeError('Unable to get version string')

	version = version_match.group(1)


requirements = [
	'bibtexparser~=1.1',
	'click~=7.0',
]

setup_requirements = ['pytest-runner']

test_requirements = ['pytest']


setup(
	name='paperpile-tools',
	version=version,
	description='Tools for extracting data from Paperpile exports.',
	long_description=readme_contents,
	author='Jared Lumpe',
	author_email='mjlumpe@gmail.com',
	url='https://github.com/jlumpe/paperpile-tools',
	python_requires='>=3.5',
	install_requires=requirements,
	setup_requires=setup_requirements,
	tests_require=test_requirements,
	include_package_data=True,
	entry_points='''
		[console_scripts]
		pptools=paperpile_tools.cli:cli
	''',
	# license='',
	# classifiers='',
	# keywords=[],
	# platforms=[],
	# provides=[],
	# requires=[],
	# obsoletes=[],
)
