from collections.abc import MutableMapping, Mapping, MutableSet
import os
from glob import glob
import string
import itertools


class Bijection(MutableSet):
	"""A bidirectional mapping.

	A bijection between the sets :attr:`left` and :attr:`right`. The bijection
	may be updated by updating the :attr:`ltr` and :attr:`rtl` attributes in
	place. Behaves as a set of ``(left, right)`` pairs.

	Properties
	----------
	ltr : .Bijection.BijectionMap
		Mapping from left keys to right keys.
	rtl : .Bijection.BijectionMap
		Mapping from right keys to left keys.
	left
		Collection of left keys (read-only).
	right
		Collection of right keys (read-only).
	"""
	class BijectionMap(MutableMapping):
		"""A mapping from one side of a bijection to the other."""
		def __init__(self, other):
			self.other = other
			self.dict = {}

		def __len__(self):
			return len(self.dict)

		def __iter__(self):
			return iter(self.dict)

		def __contains__(self, value):
			return value in self.dict

		def __getitem__(self, key):
			return self.dict[key]

		def __setitem__(self, key, value):
			if key in self.dict:
				value2 = self.dict[key]
				if value2 != value:
					raise KeyError('Key %r already exists with different value %r' % (key, value2))
				return

			if value in self.other.dict:
				key2 = self.other.dict[value]
				if key2 != key:
					raise KeyError('Value %r already exists with key %r' % (value, key2))
				return

			self.dict[key] = value
			self.other.dict[value] = key

		def __delitem__(self, key):
			value = self.dict.pop(key)
			del self.other.dict[value]


	def __init__(self, pairs=None):
		"""
		Parameters
		----------
		pairs
			Existing ``Bijection`` instance or collection of ``(left, right)``
			pairs.
		"""

		self.ltr = Bijection.BijectionMap(None)
		self.rtl = Bijection.BijectionMap(self.ltr)
		self.ltr.other = self.rtl

		if isinstance(pairs, Bijection):
			self.ltr.update(pairs.ltr)

		elif pairs is not None:
			for left, right in pairs:
				self.ltr[left] = right

	@staticmethod
	def from_ltr(self, mapping):
		"""Create new bijection from left-to-right mapping."""
		b = Bijection()
		b.ltr.update(mapping)

	@staticmethod
	def from_rtl(self, mapping):
		"""Create new bijection from right-to-left mapping."""
		b = Bijection()
		b.rtl.update(mapping)

	@property
	def left(self):
		return self.ltr.keys()

	@property
	def right(self):
		return self.rtl.keys()

	def __len__(self):
		return len(self.ltr)

	def __iter__(self):
		return iter(self.ltr.items())

	def __contains__(self, pair):
		if not isinstance(pair, tuple) or len(pair) != 2:
			return False
		left, right = pair
		return left in self.ltr and self.ltr[left] == right

	def add(self, pair):
		left, right = pair
		self.ltr[left] = right

	def discard(self, pair):
		if pair not in self:
			raise KeyError(pair)
		left, right = pair
		del self.ltr[left]

	def update_left(self, other):
		"""Update with another bijection, merging keys on the left."""
		if not isinstance(other, Bijection):
			other = Bijection.from_ltr(other)
		self._update(self.ltr, other.ltr)

	def update_right(self, other):
		"""Update with another bijection, merging keys on the right."""
		if not isinstance(other, Bijection):
			other = Bijection.from_rtl(other)
		self._update(self.rtl, other.rtl)

	def _update(self, self_map, other_map):
		for key in other_map:
			try:
				del self_map[key]
			except KeyError:
				continue

		self_map.update(other_map)


def get_bijection(arg, dir='ltr'):
	"""Get Bijection from argument, accepting mappings.

	Parameters
	----------
	arg
		:class:`.Bijection` instance or mapping.
	dir : str
		Direction of ``arg`` if it is a mapping. One of ``['ltr', 'rtl']``.

	Returns
	-------
	.Bijection
	"""
	if isinstance(arg, Bijection):
		return arg
	if dir == 'ltr':
		return Bijection.from_ltr(arg)
	elif dir == 'rtl':
		return Bijection.from_rtl(arg)
	else:
		raise ValueError("dir must be one of ['ltr', 'rtl']")


def find_pp_bibtex_all(directory):
	"""Find all Paperpile export files in directory by file name."""
	pattern = os.path.join(directory, 'Paperpile - * BibTeX Export*.bib')
	return [os.path.join(directory, f) for f in glob(pattern)]


def find_pp_bibtex(directory):
	"""Find most recent Paperpile export file in directory by name."""
	mostrecent = None
	mostrecent_time = 0

	for file in find_pp_bibtex_all(directory):
		ctime = os.stat(file).st_ctime
		if ctime > mostrecent_time:
			mostrecent = file
			mostrecent_time = ctime

	return mostrecent


def iter_letters():
	"""Iterate over all non-empty strings of lower case letters, shortest first."""
	i = 1
	while True:
		sets = [string.ascii_lowercase] * i
		for letters in itertools.product(*sets):
			yield ''.join(letters)
		i += 1
