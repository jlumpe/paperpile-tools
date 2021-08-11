from typing import MutableMapping, MutableSet, Tuple, Any, Optional, Iterable, Mapping, Union, Dict,\
	Collection, TypeVar
from enum import IntEnum
import os
import string
import itertools
from contextlib import contextmanager
import re


L = TypeVar('L')
R = TypeVar('R')


class KeyLoc(IntEnum):
	"""Location of a key in a Bijection key pair.

	Either absolute (LEFT/RIGHT) or relative to one side
	(FROM/TO).
	"""

	LEFT  = 0
	RIGHT = 1
	FROM  = 2
	TO    = 3

	@property
	def relative(self) -> bool:
		return bool(self & 2)

	@staticmethod
	def _checkabs(side):
		if not isinstance(side, KeyLoc):
			raise TypeError(type(side))
		if side.relative:
			raise ValueError(side)

	def toabs(self, fromside):
		self._checkabs(fromside)
		if not self.relative:
			return self
		return KeyLoc((self & 1) ^ fromside)

	def torel(self, fromside):
		self._checkabs(fromside)
		if self.relative:
			return self
		return KeyLoc((self ^ fromside) | 2)

	def flip(self):
		return KeyLoc(self ^ 1)


class BijectionKeyConflict(KeyError):
	"""KeyError that occurs when adding/assigning to a :class:`.Bijection`.

	Attributes
	----------
	keypair : tuple
		The ``(left, right)`` (if adding to a Bijection) or
		``(from, to)`` (if assigning to BijectionMap)
		pair that caused the problem.
	side : KeyLoc
		Side of the key pair that the conflict occurred on.
	current
		Existing key value that caused the conflict.
	"""
	keypair: Tuple[Any, Any]
	side: KeyLoc
	current: Any

	def __init__(self, keypair: Tuple[Any, Any], side: KeyLoc, current: Any):
		self.keypair = keypair
		self.side = side
		self.current = current

	def toabs(self, fromside: KeyLoc) -> 'BijectionKeyConflict':
		KeyLoc._checkabs(fromside)
		if not self.side.relative:
			return self

		absside = self.side.toabs(fromside)
		pair = self.keypair if fromside is KeyLoc.LEFT else self.keypair[::-1]
		return BijectionKeyConflict(pair, absside, self.current)

	def torel(self, fromside: KeyLoc) -> 'BijectionKeyConflict':
		KeyLoc._checkabs(fromside)
		if self.side.relative:
			return self

		relside = self.side.torel(fromside)
		pair = self.keypair if fromside is KeyLoc.LEFT else self.keypair[::-1]
		return BijectionKeyConflict(pair, relside, self.current)


class BijectionMap(MutableMapping[L, R]):
	"""A mapping from one side of a :class:`.Bijection` to the other.

	Properties
	----------
	other
		The reverse mapping
	"""
	other: 'BijectionMap[R, L]'
	dict: Dict[L, R]

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
				raise BijectionKeyConflict((key, value), KeyLoc.TO, value2)
			return

		if value in self.other.dict:
			key2 = self.other.dict[value]
			if key2 != key:
				raise BijectionKeyConflict((key, value), KeyLoc.FROM, key2)
			return

		self.dict[key] = value
		self.other.dict[value] = key

	def __delitem__(self, key):
		value = self.dict.pop(key)
		del self.other.dict[value]


class Bijection(MutableSet[Tuple[L, R]]):
	"""A bidirectional mapping.

	A bijection between the sets :attr:`left` and :attr:`right`. The bijection
	may be updated by updating the :attr:`ltr` and :attr:`rtl` attributes in
	place. Behaves as a set of ``(left, right)`` pairs.

	Properties
	----------
	ltr
		Mapping from left keys to right keys.
	rtl
		Mapping from right keys to left keys.
	left
		Collection of left keys (read-only).
	right
		Collection of right keys (read-only).
	"""
	ltr: BijectionMap[L, R]
	rtl: BijectionMap[R, L]

	def __init__(self, pairs: Optional[Iterable[Tuple[L, R]]]=None):
		"""
		Parameters
		----------
		pairs
			Existing ``Bijection`` instance or collection of ``(left, right)``
			pairs.
		"""

		self.ltr = BijectionMap(None)
		self.rtl = BijectionMap(self.ltr)
		self.ltr.other = self.rtl

		self.left = self.ltr.keys()
		self.right = self.rtl.keys()

		if isinstance(pairs, Bijection):
			self.ltr.update(pairs.ltr)

		elif pairs is not None:
			for left, right in pairs:
				self.ltr[left] = right

	@staticmethod
	def from_ltr(mapping: Mapping[L, R]) -> 'Bijection[L, R]':
		"""Create new bijection from left-to-right mapping."""
		b = Bijection()
		b.ltr.update(mapping)
		return b

	@staticmethod
	def from_rtl(mapping: Mapping[R, L]) -> 'Bijection[L, R]':
		"""Create new bijection from right-to-left mapping."""
		b = Bijection()
		b.rtl.update(mapping)
		return b

	@staticmethod
	def identity(keys: Iterable[L]) -> 'Bijection[L, L]':
		"""Create an identity bijection that maps each key to itself."""
		return Bijection((k, k) for k in keys)

	def __len__(self):
		return len(self.ltr)

	def __iter__(self):
		return iter(self.ltr.items())

	def __contains__(self, pair):
		if not isinstance(pair, tuple) or len(pair) != 2:
			return False
		left, right = pair
		return left in self.ltr and self.ltr[left] == right

	def add(self, pair: Tuple[L, R]):
		left, right = pair
		try:
			self.ltr[left] = right
		except BijectionKeyConflict as e:
			raise e.toabs(KeyLoc.LEFT) from e

	def discard(self, pair: Tuple[L, R]):
		if pair not in self:
			raise KeyError(pair)
		left, right = pair
		del self.ltr[left]

	def update_left(self, other: Union['Bijection', Mapping[L, R]]):
		"""Update with another bijection, merging keys on the left."""
		if not isinstance(other, Bijection):
			other = Bijection.from_ltr(other)
		try:
			self._update(self.ltr, other.ltr)
		except BijectionKeyConflict as e:
			raise e.toabs(KeyLoc.LEFT) from e

	def update_right(self, other: Union['Bijection', Mapping[R, L]]):
		"""Update with another bijection, merging keys on the right."""
		if not isinstance(other, Bijection):
			other = Bijection.from_rtl(other)
		try:
			self._update(self.rtl, other.rtl)
		except BijectionKeyConflict as e:
			raise e.toabs(KeyLoc.RIGHT) from e

	def _update(self, self_map, other_map):
		for key in other_map:
			try:
				del self_map[key]
			except KeyError:
				continue

		self_map.update(other_map)

	def conflicts(self, other: 'Bijection') -> Tuple[Dict, Dict]:
		"""Find key conflicts with another bijection."""
		ltr = {}
		rtl = {}

		for left in self.left & other.left:
			v1 = self.ltr[left]
			v2 = other.ltr[left]
			if v1 != v2:
				ltr[left] = v1, v2

		for right in self.right & other.right:
			v1 = self.rtl[right]
			v2 = other.ltr[right]
			if v1 != v2:
				rtl[right] = v1, v2

		return ltr, rtl


def get_bijection(arg: Union[Bijection, Mapping], dir: str = 'ltr') -> Bijection:
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


@contextmanager
def _file_context_file(file):
	yield file

@contextmanager
def _file_context_str(file, mode, **kw):
	with open(file, mode=mode, **kw) as f:
		yield f

def file_context(file, mode='r', **kw):
	"""

	Parameters
	----------
	file : str or open file object

	Returns
	-------
	Context manager which returns open file object on enter and exits on close
	if needed.
	"""
	return _file_context_str(file, mode, **kw) if isinstance(file, str) else _file_context_file(file)
