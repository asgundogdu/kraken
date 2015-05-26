"""
Various add-ons to the SciPy morphology package
"""

from __future__ import absolute_import, division, print_function

import numpy as np
from scipy.ndimage import morphology, measurements, filters


def label(image, **kw):
    """
    Redefine the scipy.ndimage.measurements.label function to work with a wider
    range of data types.  The default function is inconsistent about the data
    types it accepts on different platforms.
    """
    try:
        return measurements.label(image, **kw)
    except:
        pass
    types = ["int32", "uint32", "int64", "unit64", "int16", "uint16"]
    for t in types:
        try:
            return measurements.label(np.array(image, dtype=t), **kw)
        except:
            pass
    # let it raise the same exception as before
    return measurements.label(image, **kw)


def find_objects(image, **kw):
    """
    Redefine the scipy.ndimage.measurements.find_objects function to work with
    a wider range of data types.  The default function is inconsistent about
    the data types it accepts on different platforms.
    """
    try:
        return measurements.find_objects(image, **kw)
    except:
        pass
    types = ["int32", "uint32", "int64", "unit64", "int16", "uint16"]
    for t in types:
        try:
            return measurements.find_objects(np.array(image, dtype=t), **kw)
        except:
            pass
    # let it raise the same exception as before
    return measurements.find_objects(image, **kw)


def check_binary(image):
    assert image.dtype == 'B' or image.dtype == 'i' or image.dtype == np.dtype('bool'),\
        "array should be binary, is %s %s" % (image.dtype, image.shape)
    assert np.amin(image) >= 0 and np.amax(image) <= 1,\
        "array should be binary, has values %g to %g" % (np.amin(image),
                                                         np.amax(image))


def r_dilation(image, size, origin=0):
    """Dilation with rectangular structuring element using maximum_filter"""
    return filters.maximum_filter(image, size, origin=origin)


def r_erosion(image, size, origin=0):
    """Erosion with rectangular structuring element using maximum_filter"""
    return filters.minimum_filter(image, size, origin=origin)


def r_opening(image, size, origin=0):
    """Opening with rectangular structuring element using maximum/minimum
    filter"""
    check_binary(image)
    image = r_erosion(image, size, origin=origin)
    return r_dilation(image, size, origin=origin)


def r_closing(image, size, origin=0):
    """Closing with rectangular structuring element using maximum/minimum
    filter"""
    check_binary(image)
    image = r_dilation(image, size, origin=0)
    return r_erosion(image, size, origin=0)


def rb_dilation(image, size, origin=0):
    """Binary dilation using linear filters."""
    output = np.zeros(image.shape, 'f')
    filters.uniform_filter(image, size, output=output, origin=origin,
                           mode='constant', cval=0)
    return np.array(output > 0, 'i')


def rb_erosion(image, size, origin=0):
    """Binary erosion using linear filters."""
    output = np.zeros(image.shape, 'f')
    filters.uniform_filter(image, size, output=output, origin=origin,
                           mode='constant', cval=1)
    return np.array(output == 1, 'i')


def rb_opening(image, size, origin=0):
    """Binary opening using linear filters."""
    image = rb_erosion(image, size, origin=origin)
    return rb_dilation(image, size, origin=origin)


def rb_closing(image, size, origin=0):
    """Binary closing using linear filters."""
    image = rb_dilation(image, size, origin=origin)
    return rb_erosion(image, size, origin=origin)


def rg_dilation(image, size, origin=0):
    """Grayscale dilation with maximum/minimum filters."""
    return filters.maximum_filter(image, size, origin=origin)


def rg_erosion(image, size, origin=0):
    """Grayscale erosion with maximum/minimum filters."""
    return filters.minimum_filter(image, size, origin=origin)


def rg_opening(image, size, origin=0):
    """Grayscale opening with maximum/minimum filters."""
    image = r_erosion(image, size, origin=origin)
    return r_dilation(image, size, origin=origin)


def rg_closing(image, size, origin=0):
    """Grayscale closing with maximum/minimum filters."""
    image = r_dilation(image, size, origin=0)
    return r_erosion(image, size, origin=0)


def spread_labels(labels, maxdist=9999999):
    """Spread the given labels to the background"""
    distances, features = morphology.distance_transform_edt(labels == 0,
                                                            return_distances=1,
                                                            return_indices=1)
    indexes = features[0] * labels.shape[1] + features[1]
    spread = labels.ravel()[indexes.ravel()].reshape(*labels.shape)
    spread *= (distances < maxdist)
    return spread


def correspondences(labels1, labels2):
    """Given two labeled images, compute an array giving the correspondences
    between labels in the two images."""
    q = 100000
    assert np.amin(labels1) >= 0 and np.amin(labels2) >= 0
    assert np.amax(labels2) < q
    combo = labels1 * q + labels2
    result = np.unique(combo)
    result = np.array([result // q, result % q])
    return result


def propagate_labels_simple(regions, labels):
    """Given an image and a set of labels, apply the labels
    to all the regions in the image that overlap a label."""
    rlabels, _ = label(regions)
    cors = correspondences(rlabels, labels)
    outputs = np.zeros(np.amax(rlabels) + 1, 'i')
    for o, i in cors.T:
        outputs[o] = i
    outputs[0] = 0
    return outputs[rlabels]


def propagate_labels(image, labels, conflict=0):
    """Given an image and a set of labels, apply the labels
    to all the regions in the image that overlap a label.
    Assign the value `conflict` to any labels that have a conflict."""
    rlabels, _ = label(image)
    cors = correspondences(rlabels, labels)
    outputs = np.zeros(np.amax(rlabels) + 1, 'i')
    oops = -(1 << 30)
    for o, i in cors.T:
        if outputs[o] != 0:
            outputs[o] = oops
        else:
            outputs[o] = i
    outputs[outputs == oops] = conflict
    outputs[0] = 0
    return outputs[rlabels]


def select_regions(binary, f, min=0, nbest=100000):
    """Given a scoring function f over slice tuples (as returned by
    find_objects), keeps at most nbest regions whose scores is higher
    than min."""
    labels, n = label(binary)
    objects = find_objects(labels)
    scores = [f(o) for o in objects]
    best = np.argsort(scores)
    keep = np.zeros(len(objects) + 1, 'i')
    for i in best[-nbest:]:
        if scores[i] <= min:
            continue
        keep[i+1] = 1
    return keep[labels]