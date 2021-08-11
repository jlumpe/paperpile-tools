"""General Bibtex stuff."""

from typing import Union, Optional, Mapping, Iterable, Collection, Callable, TextIO, Dict, Any, List,\
	Tuple

from bibtexparser import load as load_bibtex
from bibtexparser.bparser import BibTexParser
from bibtexparser.customization import homogenize_latex_encoding
from bibtexparser.bibdatabase import BibDatabase
from bibtexparser.bwriter import BibTexWriter

from pptools.util import Bijection, get_bijection, maybe_open, FilePath


__all__ = ['check_db', 'check_entries', 'make_db', 'merge_dbs',
           'read_bibliography', 'extract_keymap', 'make_keymap',
           'update_keys', 'revert_keys', 'write_bibliography', 'entry_diff',
           'find_duplicate_keys']


# Type aliases
KeyMap = Bijection[str, str]
KeyMapArg = Union[KeyMap, Mapping[str, str]]
BibEntry = Dict[str, Any]


def check_entries(entries: Iterable[BibEntry]):
	"""Validate list of entries."""
	# Just check for duplicate keys
	allkeys = set()
	for entry in entries:
		if entry['ID'] in allkeys:
			raise KeyError('Duplicate ID %r' % entry['ID'])
		allkeys.add(entry['ID'])


def check_db(db: BibDatabase) -> None:
	"""Check bibtex database for issues.

	Parameters
	----------
	db : BibDatabase

	Raises
	------
	KeyError
		Duplicate key is present
	"""
	check_entries(db.entries)


def make_db(entries: Iterable[BibEntry]) -> BibDatabase:
	"""Make bibtex database from list of entry dictionaries.

	Parameters
	----------
	entries : list of dict

	Returns
	-------
	BibDatabase
	"""
	entries = list(entries)
	check_entries(entries)
	db = BibDatabase()
	db.entries = entries
	return db


def merge_dbs(*dbs: BibDatabase) -> BibDatabase:
	"""Merge databases together."""
	entries_dict = {}
	for db in dbs:
		entries_dict.update(db.entries_dict)
	return make_db(entries_dict.values())


def default_parser() -> BibTexParser:
	"""Get a Bibtex parser with default settings."""
	parser = BibTexParser(common_strings=True)
	# parser.customization = homogenize_latex_encoding
	return parser


def read_bibliography(file: Union[FilePath, TextIO], check: bool = False) -> BibDatabase:
	"""Read .bib file.

	Parameters
	----------
	file : str or open file object
	check : bool
		Check database for issues and raise exception if any are found.
	"""
	parser = default_parser()

	with maybe_open(file, encoding='utf-8') as f:
		db = load_bibtex(f, parser)

	if check:
		check_db(db)

	return db


def make_key_sub_comment(keymap: KeyMapArg, omitted: Collection[str] = None) -> str:
	"""Make a comment for a bibliography file indicating key substitutions.

	Parameters
	----------
	keymap : dict or Bijection
	omitted : list
		List of omitted keys (not present in new bibliography)
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


def find_duplicate_keys(db: BibDatabase, attr: Optional[str] = None, f: Optional[Callable] = None) -> Dict[str, List]:
	"""Find duplicate keys.

	Parameters
	----------
	db : BibDatabase
	attr : str
		Entry attribute to look up. If None use the entry's Bibtex ID.
	f : callable
		Function with signature ``(entry, key) -> newkey`` which normalizes
		the key before comparison.

	Returns
	-------
	dict
	"""
	seen = dict()

	for i, entry in enumerate(db.entries):
		id_ = entry['ID']

		try:
			key = id_ if attr is None else entry[attr]
		except KeyError:
			continue

		if f is not None:
			key = f(entry, key)

		value = i if attr is None else id_
		seen.setdefault(key, []).append(value)

	return {k: v for k, v in seen.items() if len(v) > 1}


def entry_diff(e1: BibEntry, e2: BibEntry, f: Optional[Callable] = None) -> Dict[str, Tuple[Any, Any]]:
	"""Find the attribute values for which two entries differ.

	This is mostly intended to be used in resolving duplicates.

	Parameters
	----------
	e1
		First entry.
	e2
		Second entry.
	f
		Function with signature ``(entry, attrname, value)`` which normalizes
		the values for comparison.

	Returns
	-------
	dict
		Mapping from attribute name to ``(e1_value, e2_value)`` pairs for
		attributes in which the values are not equal.
	"""
	diff = {}
	for key in e1.keys() & e2.keys():
		if key == 'ID':
			continue

		v1 = e1[key]
		v2 = e2[key]
		if f is not None:
			v1 = f(e1, key, v1)
			v2 = f(e2, key, v2)

		if v1 != v2:
			diff[key] = (v1, v2)

	return diff


def extract_keymap(db: BibDatabase, attr: str) -> KeyMap:
	"""Extract key map from existing bibliography.

	Parameters
	----------
	db
	attr
		Attribute name to get original key from

	Returns
	-------
	Bijection
		Bijection between Paperpile keys and replacement keys.

	Raises
	------
	KeyError
		If duplicate keys are found.
	"""
	keymap = Bijection()
	for key, entry in db.entries_dict.items():
		try:
			orig_key = entry[attr]
		except KeyError:
			continue

		keymap.add((orig_key, key))

	return keymap


def make_keymap(keys: Iterable[str], f: Callable) -> Tuple[KeyMap, Dict[str, List[str]]]:
	"""Create keymap according to function, detecting and omitting duplicate assignments.

	Parameters
	----------
	keys
		List of existing keys.
	f : callable
		Function which takes an existing key and returns the updated key.

	Returns
	-------
	tuple
		Tuple of ``(updates, conflicts)``. ``updates`` is a
		:class:`Bijection` of ``old_keys <-> new_keys``
		and ``conflicts`` is a mapping from new keys to lists of old keys that
		map to it.
	"""
	updates = Bijection()

	revmap = {}
	for key in keys:
		newkey = f(key)
		if newkey != key:
			revmap.setdefault(newkey, []).append(key)

	conflicts = {}

	for newkey, oldkeys in revmap.items():
		if len(oldkeys) == 1:
			updates.ltr[oldkeys[0]] = newkey
		else:
			conflicts[newkey] = oldkeys

	return updates, conflicts


def update_keys(db: BibDatabase, keymap: KeyMapArg, save_attr: Optional[str] = None) -> BibDatabase:
	"""Replace keys in bibtex database using keymap.

	Parameters
	----------
	db
	keymap : dict or Bijection
	save_attr
		Attribute name to store original key for each updated entry.
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
		if save_attr is not None:
			if save_attr in entry:
				pass  # TODO
			entry[save_attr] = oldkey

	return make_db(entries)


def revert_keys(db: BibDatabase, attr: str, inplace: bool = False):
	"""Revert keys in database to their original values.

	Parameters
	----------
	db
	attr
		Attribute name containing the original key values.
	inplace
		Update bibliography in place instead of returning a new one.
	"""
	entries = db.entries
	if not inplace:
		entries = list(map(dict, entries))

	for entry in entries:
		try:
			entry['ID'] = entry.pop(attr)
		except KeyError:
			continue

	return make_db(entries) if inplace else db


def write_bibliography(file: Union[FilePath, TextIO], db: BibDatabase):
	"""Write bibliography entries to new file."""
	writer = BibTexWriter()
	writer.indent = '    '

	with maybe_open(file, 'w', encoding='utf-8') as f:
		f.write(writer.write(db))
