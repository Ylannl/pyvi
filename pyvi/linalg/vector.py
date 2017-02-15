# -*- coding: utf-8 -*-

"""
Basic 3D vector operations.

Copyright (c) 2010, Renaud Blanch <rndblnch at gmail dot com>
Licence: GPLv3 or higher <http://www.gnu.org/licenses/gpl.html>
"""

# imports ####################################################################

from math import sqrt as _sqrt
_sum = sum


# globals ####################################################################

def _zip_zero_pad(*ps):
	len_max = max(len(p) for p in ps)
	ps = [tuple(p) + (0.,)*(len_max-len(p)) for p in ps]
	for t in zip(*ps):
		yield t

_O = tuple()
_3D = 3
_X, _Y, _Z = list(range(_3D))


# vector #####################################################################

def vector(p1=_O, p0=_O):
	return tuple(p1i-p0i for (p1i, p0i) in _zip_zero_pad(p1, p0))

def mul(a, v):
	return tuple(a*vi for vi in v)

def add(u, v):
	return tuple(ui+vi for (ui, vi) in _zip_zero_pad(u, v))

def sum(u=vector(), *vs):
	for v in vs:
		u = add(u, v)
	return u

def sub(u, v):
	return tuple(ui-vi for (ui, vi) in _zip_zero_pad(u, v))

def dot(u, v):
	return _sum(ui*vi for (ui, vi) in _zip_zero_pad(u, v))

def cross(u, v):
	assert len(u) == len(v) == _3D
	return (u[_Y]*v[_Z]-u[_Z]*v[_Y],
	        u[_Z]*v[_X]-u[_X]*v[_Z],
	        u[_X]*v[_Y]-u[_Y]*v[_X])

def norm(v):
	return _sqrt(dot(v, v))

def matrix(v):
	return [[vi] for vi in v]
