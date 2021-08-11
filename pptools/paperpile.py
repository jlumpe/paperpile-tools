"""PaperPile-specific code."""

import re
import os
from glob import glob

from bibtexparser.bibdatabase import BibDatabase

from .util import BijectionKeyConflict, KeyLoc, str_replace_map
from .bibliography import extract_keymap, KeyMap


__all__ = ['PP_ATTR', 'remove_pp_suffix', 'extract_pp_keymap', 'find_pp_bib_all',
           'find_pp_bib', 'normalize_pp_key']


#: Attribute to store original PaperPile key in
PP_ATTR = 'paperpile_key'


#:
KEY_NORM_MAP = {
	r'\\_': '_',  # Escaped underscore?
	r'\s+': ' ',  # Shorten whitespace
	r'{(\w+)}': '\\1',  # Weird brackets around words
}


def normalize_pp_key(key: str) -> str:
	"""Normalize a paperpile key."""
	return str_replace_map(KEY_NORM_MAP, key, regex=True)


def remove_pp_suffix(key: str) -> str:
	"""Remove extra characters Paperpile appends to a Bibtex key."""
	if re.fullmatch(r'.*?-[A-Za-z]{2}$', key):
		return key[:-3]
	return key


def extract_pp_keymap(db: BibDatabase) -> KeyMap:
	try:
		return extract_keymap(db, PP_ATTR)

	except BijectionKeyConflict as e:
		pp_key, key = e.keypair
		if e.side is KeyLoc.RIGHT:
			raise ValueError(
				'Replacement key %r appears twice, corresponding to paperpile keys %r and %r'
				% (key, pp_key, e.current)
			) from None
		elif e.side is KeyLoc.LEFT:
			raise ValueError(
				'Paperpile key %r appears twice, corresponding to replacement keys %r and %r'
				% (pp_key, key, e.current)
			) from None
		else:
			assert 0


def find_pp_bib_all(directory):
	"""Find all Paperpile export files in directory by file name."""
	pattern = os.path.join(directory, 'Paperpile - * BibTeX Export*.bib')
	return [os.path.join(directory, f) for f in glob(pattern)]


def find_pp_bib(directory):
	"""Find most recent PaperPile export file in directory by name.

	Note - this works of the creation time in the file's metadata, not by parsing
	the date from the file's name.
	"""
	mostrecent = None
	mostrecent_time = 0

	for file in find_pp_bib_all(directory):
		ctime = os.stat(file).st_ctime
		if ctime > mostrecent_time:
			mostrecent = file
			mostrecent_time = ctime

	return mostrecent
