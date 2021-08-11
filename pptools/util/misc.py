from typing import MutableMapping, MutableSet, Tuple, Any, Optional, Iterable, Mapping, Union, Dict,\
	Collection, TypeVar, IO, ContextManager
from enum import IntEnum
import os
import string
import itertools
from contextlib import nullcontext
import re

FilePath = Union[str, os.PathLike]



def iter_letters() -> Iterable[str]:
	"""Iterate over all non-empty strings of lower case letters, shortest first."""
	i = 1
	while True:
		sets = [string.ascii_lowercase] * i
		for letters in itertools.product(*sets):
			yield ''.join(letters)
		i += 1


def dedup_key(key: str, existing: Collection[str], sep: str = '') -> str:
	"""Deduplicate a key by adding a suffix to it.

	Parameters
	----------
	key
		Key to make unique.
	existing
		Existing keys to avoid conflicts with.
	sep : str
		Separator between ``key`` and suffix.

	Returns
	-------
	str
		``key`` with suffix added such that it does not match any keys in ``existing``.
	"""
	for suffix in iter_letters():
		# Special case - consider the first "a" suffix to be equal to original key
		if suffix == 'a' and key in existing:
			continue
		newkey  = key + sep + suffix
		if newkey not in existing:
			return newkey


def str_replace_map(d: Mapping[str, str], s: str, regex: bool = False) -> str:
	"""Replace multiple substrings at once using a mapping.

	Parameters
	----------
	d : mapping
		Mapping from substrings to replacements
	s : str
		String to replace within

	Returns
	-------
	str
		String with replacements made
	"""
	for (pattern, replacement) in d.items():
		if regex:
			s = re.sub(pattern, replacement, s)
		else:
			s = s.replace(pattern, replacement)
	return s


def maybe_open(file_or_path: Union[FilePath, IO], mode: str = 'r', **open_kw) -> ContextManager[IO]:
	"""Open a file given a file path as an argument, but pass existing file objects though.

	Intended to be used by API functions that take either type as an argument. If a file path is
	passed the function will need to call ``open`` to get the file object to use, and will need to
	close that object after it is done. If an existing file object is passed, it should be left to
	the caller of the function to close it afterwards. This function returns a context manager which
	performs the correct action for both opening and closing.

	Parameters
	----------
	file_or_path
		A path-like object or open file object.
	mode
		Mode to open file in.
	\\**open_kw
		Keyword arguments to :func:`open`.

	Returns
	-------
	ContextManager[IO]
		Context manager which gives an open file object on enter and closes it on exit only if it
		was opened by this function.
	"""
	try:
		# Try to interpret as path
		path = os.fspath(file_or_path)
	except TypeError:
		# Not a path, assume file object
		# Return context manager which gives this object on enter and does not close on exit
		return nullcontext(file_or_path)
	else:
		# Is a path, just open
		return open(path, mode, **open_kw)
