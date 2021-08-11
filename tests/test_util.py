import pytest

from pptools.util.bijection import Bijection, KeyLoc, BijectionKeyConflict


def test_KeyLoc():
	left = KeyLoc.LEFT
	right = KeyLoc.RIGHT
	from_ = KeyLoc.FROM
	to_ = KeyLoc.TO

	# relative attribute
	assert not left.relative
	assert not right.relative
	assert from_.relative
	assert to_.relative

	# Inversion
	assert left.flip() is right
	assert right.flip() is left
	assert from_.flip() is to_
	assert to_.flip() is from_

	# toabs
	assert left.toabs(left) is left
	assert left.toabs(right) is left
	assert right.toabs(left) is right
	assert right.toabs(right) is right
	assert from_.toabs(left) is left
	assert from_.toabs(right) is right
	assert to_.toabs(left) is right
	assert to_.toabs(right) is left

	# torel
	assert left.torel(left) is from_
	assert left.torel(right) is to_
	assert right.torel(left) is to_
	assert right.torel(right) is from_
	assert from_.torel(left) is from_
	assert from_.torel(right) is from_
	assert to_.torel(left) is to_
	assert to_.torel(right) is to_


def test_BijectionKeyConflict():
	# toabs()
	e = BijectionKeyConflict((0, 1), KeyLoc.FROM, 123)
	assert e.toabs(KeyLoc.LEFT).args == ((0, 1), KeyLoc.LEFT, 123)
	assert e.toabs(KeyLoc.RIGHT).args == ((1, 0), KeyLoc.RIGHT, 123)

	e = BijectionKeyConflict((0, 1), KeyLoc.TO, 123)
	assert e.toabs(KeyLoc.LEFT).args == ((0, 1), KeyLoc.RIGHT, 123)
	assert e.toabs(KeyLoc.RIGHT).args == ((1, 0), KeyLoc.LEFT, 123)

	# torel()
	e = BijectionKeyConflict((0, 1), KeyLoc.LEFT, 123)
	assert e.torel(KeyLoc.LEFT).args == ((0, 1), KeyLoc.FROM,  123)
	assert e.torel(KeyLoc.RIGHT).args == ((1, 0), KeyLoc.TO, 123)

	e = BijectionKeyConflict((0, 1), KeyLoc.RIGHT, 123)
	assert e.torel(KeyLoc.LEFT).args == ((0, 1), KeyLoc.TO, 123)
	assert e.torel(KeyLoc.RIGHT).args == ((1, 0), KeyLoc.FROM, 123)


def test_Bijection_add_conflict():
	b = Bijection([(1, -1), (2, -2), (3, -3)])

	pair = (1, None)
	with pytest.raises(BijectionKeyConflict) as excinfo:
		b.add(pair)

	e = excinfo.value
	assert isinstance(e, BijectionKeyConflict)
	assert e.args == (pair, KeyLoc.RIGHT, -1)

	pair = (None, -1)
	with pytest.raises(BijectionKeyConflict) as excinfo:
		b.add(pair)

	e = excinfo.value
	assert isinstance(e, BijectionKeyConflict)
	assert e.args == (pair, KeyLoc.LEFT, 1)
