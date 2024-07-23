"""reduction op"""
import mindspore
from mindspore import ops
from mindnlp.configs import USE_PYBOOST

# argmax
def argmax(input, dim=None, keepdim=False):
    if USE_PYBOOST:
        return mindspore.mint.argmax(input, dim, keepdim)
    return ops.argmax(input, dim, keepdim)

# argmin
def argmin(input, dim=None, keepdim=False):
    return ops.argmin(input, dim, keepdim)

# amax
def amax(input, dim, keepdim=False):
    return ops.amax(input, dim, keepdim)

# amin
def amin(input, dim, keepdim=False):
    return ops.amin(input, dim, keepdim)

# aminmax
def aminmax(input, *, dim=None, keepdim=False):
    if dim is None:
        dim = ()
    return amin(input, dim, keepdim), amax(input, dim, keepdim)

# all
def all(input, dim, keepdim=False, *, dtype=None):
    if USE_PYBOOST:
        return mindspore.mint.all(input, dim, keepdim)
    return ops.all(input, dim, keepdim)

# any
def any(input, dim=None, keepdim=False):
    if USE_PYBOOST:
        return mindspore.mint.any(input, dim, keepdim)
    return ops.any(input, dim, keepdim)

# max
def max(input, dim=None, keepdim=False):
    if USE_PYBOOST:
        return mindspore.mint.max(input, dim, keepdim)
    out = ops.max(input, dim, keepdim)
    if dim is None:
        return out[0]
    return out

# min
def min(input, dim=None, keepdim=False):
    if USE_PYBOOST:
        return mindspore.mint.min(input, dim, keepdim)
    return ops.min(input, dim, keepdim)

# dist

# logsumexp

# mean
def mean(input, dim, keepdim=False, *, dtype=None):
    if USE_PYBOOST:
        return mindspore.mint.mean(input, dim, keepdim, dtype=dtype)
    out = ops.mean(input, dim, keepdim)
    if dtype is not None:
        out = out.astype(dtype)
    return out

# nanmean


# median
def median(input, dim=-1, keepdim=False):
    return ops.median(input, dim, keepdim)

# nanmedian
def nanmedian(input, dim=-1, keepdim=False):
    return ops.nanmedian(input, dim, keepdim)

# mode


# norm

# nansum


# prod
def prod(input, dim, keepdim=False, *, dtype=None):
    if USE_PYBOOST:
        return mindspore.mint.prod(input, dim, keepdim, dtype=dtype)
    return ops.prod(input, dim, keepdim).to(dtype)

# quantile
def quantile(input, q, dim=None, keepdim=False, *, interpolation='linear'):
    return ops.quantile(input, q, dim, keepdim)

# nanquantile
def nanquantile(input, q, dim=None, keepdim=False, *, interpolation='linear'):
    return ops.quantile(input, q, dim, keepdim)

# std
def std(input, dim=None, *, correction=1, keepdim=False):
    return ops.std(input, dim, correction, keepdim)

# std_mean
def std_mean(input, dim=None, *, correction=1, keepdim=False):
    return std(input, dim, correction=correction, keepdim=keepdim), \
        mean(input, dim, keepdim)

# sum
def sum(input, dim=None, keepdim=False, *, dtype=None):
    if USE_PYBOOST:
        return mindspore.mint.sum(input, dim, keepdim, dtype=dtype)
    return ops.sum(input, dim, keepdim, dtype=dtype)

# unique
def unique(input, sorted=True, return_inverse=False, return_counts=False, dim=None):
    pass

# unique_consecutive
def unique_consecutive(input, return_inverse, return_counts, dim=None):
    return ops.unique_consecutive(input, return_inverse, return_counts, dim)

# var
def var(input, dim=None, *, correction=1, keepdim=False):
    return pow(std(input, dim, correction=correction, keepdim=keepdim), 2)

# var_mean
def var_mean(input, dim=None, *, correction=1, keepdim=False):
    return pow(std(input, dim, correction=correction, keepdim=keepdim), 2), \
        mean(input, dim, keepdim)

# count_nonzero
def count_nonzero(input, dim=None):
    return ops.count_nonzero(input, dim)
