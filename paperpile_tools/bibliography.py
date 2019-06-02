import re

from bibtexparser import load as load_bibtex
from bibtexparser.bparser import BibTexParser
from bibtexparser.customization import homogenize_latex_encoding
from bibtexparser.bibdatabase import BibDatabase
from bibtexparser.bwriter import BibTexWriter

from .util import Bijection, get_bijection


def check_entries(entries):
	"""Validate list of entries."""
	# Just check for duplicate keys
	allkeys = set()
	for entry in entries:
		if entry['ID'] in allkeys:
			raise KeyError('Duplicate ID %r' % entry['ID'])
		allkeys.add(entry['ID'])


def check_db(db):
	"""Check bibtex database for issues."""
	check_entries(db.entries)


def make_db(entries):
	"""Make bibtex database from list of entry dictionaries."""
	entries = list(entries)
	check_entries(entries)
	db = BibDatabase()
	db.entries = entries
	return db


def merge_dbs(*dbs):
	"""Merge databases together."""
	entries_dict = {}
	for db in dbs:
		entries_dict.update(db.entries_dict)
	return make_db(entries_dict.values())


def reduce_key(key):
	"""Remove extra characters on the end of the bibtex key."""
	if re.fullmatch(r'.*?-[A-Za-z]{2}$', key):
		return key[:-3]
	return key


def assign_reduced_keys(keys, keymap=None):
	"""Assign reduced keys, detecting and omitting duplicate assignments.

	Parameters
	----------
	keys : iterable of str
		List of existing keys.
	keymap : dict or paperpile_tools.util.Bijection
		Existing keymap.

	Returns
	-------
	tuple
		Tuple of ``(updates, conflicts)``. ``updates`` is a
		:class:`paperpile_tools.util.Bijection` of ``old_keys <-> reduced_keys``
		and ``conflicts`` is a mapping from reduced keys to lists of keys that
		share the same reduced form.
	"""
	keymap = get_bijection(keymap)
	updates = Bijection()

	revmap = {}
	for key in keys:
		# Skip those in existing keymap
		if key in keymap.left:
			continue
		key2 = reduce_key(key)
		if key2 != key:
			revmap.setdefault(key2, []).append(key)

	conflicts = {}

	for reduced, keys in revmap.items():
		if len(keys) == 1 and reduced not in keymap.right:
			updates.ltr[keys[0]] = reduced
		else:
			conflicts[reduced] = keys

	return updates, conflicts


def read_bibliography(file, check=False):
	"""Read .bib file.

	Parameters
	----------
	file : str
	check : bool
		Check database for issues and raise exception if any are found.

	Returns
	-------
	bibtexparser.bibdatabase.BibDatabase
	"""
	parser = BibTexParser(common_strings=True)
	parser.customization = homogenize_latex_encoding
	db = load_bibtex(file, parser)
	if check:
		check_db(db)
	return db


def make_key_sub_comment(keymap, omitted=None):
	"""Replace keys in bibtex database using keymap.


	Parameters
	----------
	keymap : dict or paperpile_tools.util.Bijection
	omitted : list
		List of omitted keys

	Returns
	-------
	str
	"""
	keymap = dict(keymap)
	lines = [
		'This BibTeX file has been processed from the one exported from PaperPile.',
		'The following TSV data indicates the citation key substitutions made:',
		'',
	]

	for key in sorted(keymap):
		lines.append(key + '\t' + keymap[key])

	if omitted:
		lines.extend(['', 'The following entries were omitted:', ''])
		lines.extend(omitted)

	return '\n'.join(lines) + '\n'


def keymap_from_bibliography(db):
	"""Extract key map from existing bibliography.

	Parameters
	----------
	db : bibtexparser.bibdatabase.BibDatabase

	Returns
	-------
	paperpile_tools.util.Bijection
	"""
	keymap = Bijection()
	for key, entry in db.entries_dict.items():
		try:
			pp_key = entry['paperpile_key']
		except KeyError:
			continue

		keymap.ltr[pp_key] = key

	return keymap


def update_keys(db, keymap, store_original=True):
	"""Replace keys in bibtex database using keymap.


	Parameters
	----------
	db : bibtexparser.bibdatabase.BibDatabase
	keymap : dict or paperpile_tools.util.Bijection
	store_original : bool
		Record original Paperpile key in each entry.

	Returns
	-------
	bibtexparser.bibdatabase.BibDatabase
	"""
	keymap = get_bijection(keymap)

	entries = list(map(dict, db.entries))

	for entry in entries:
		oldkey = entry['ID']
		try:
			newkey = keymap.ltr[oldkey]
		except KeyError:
			continue

		entry['ID'] = newkey
		if store_original and 'paperpile_key' not in entry:
			entry['paperpile_key'] = oldkey

	return make_db(entries)


def revert_keys(db):
	"""Revert keys in database to their original Paperpile values."""

	entries = list(map(dict, db.entries))

	for entry in entries:
		try:
			entry['ID'] = entry.pop('paperpile_key')
		except KeyError:
			continue

	return make_db(entries)


def write_bibliography(file, db):
	"""Write bibliography entries to new file."""
	writer = BibTexWriter()
	writer.indent = '    '

	file.write(writer.write(db))
