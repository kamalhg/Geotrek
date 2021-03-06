import logging
from itertools import islice

from django.db import connection
from django.utils.timezone import utc
from django.contrib.gis.measure import Distance


logger = logging.getLogger(__name__)


class classproperty(object):
    def __init__(self, getter):
        self.getter = getter

    def __get__(self, instance, owner):
        return self.getter(owner)


# This one come from pyramid
# https://github.com/Pylons/pyramid/blob/master/pyramid/decorator.py
class reify(object):

    """ Put the result of a method which uses this (non-data)
    descriptor decorator in the instance dict after the first call,
    effectively replacing the decorator with an instance variable."""

    def __init__(self, wrapped):
        self.wrapped = wrapped
        try:
            self.__doc__ = wrapped.__doc__
        except:  # pragma: no cover
            pass

    def __get__(self, inst, objtype=None):
        if inst is None:
            return self
        val = self.wrapped(inst)
        setattr(inst, self.wrapped.__name__, val)
        return val


class LTE(int):
    """ Less or equal object comparator
    Source: https://github.com/justquick/django-activity-stream/blob/22b22297054776f7864ff642b73add15b256a2ad/actstream/tests.py
    """
    def __new__(cls, n):
        obj = super(LTE, cls).__new__(cls, n)
        obj.n = n
        return obj

    def __eq__(self, other):
        return other <= self.n

    def __repr__(self):
        return "<= %s" % self.n


def dbnow():
    cursor = connection.cursor()
    cursor.execute("SELECT statement_timestamp() AT TIME ZONE 'UTC';")
    row = cursor.fetchone()
    return row[0].replace(tzinfo=utc)


def sql_extent(sql):
    """ Given a SQL query that returns a BOX(), returns
    tuple (xmin, ymin, xmax, ymax)
    """
    cursor = connection.cursor()
    cursor.execute(sql)
    result = cursor.fetchall()
    row = result[0]
    extent = row[0] or '0 0 0 0'
    value = extent.replace('BOX(', '').replace(')', '').replace(',', ' ')
    return tuple([float(v) for v in value.split()])


def sqlfunction(function, *args):
    """
    Executes the SQL function with the specified args, and returns the result.
    """
    sql = '%s(%s)' % (function, ','.join(args))
    logger.debug(sql)
    cursor = connection.cursor()
    cursor.execute(sql)
    result = cursor.fetchall()
    if len(result) == 1:
        return result[0]
    return result


def almostequal(v1, v2, precision=2):
    return abs(v1 - v2) < 10 ** -precision


def sampling(values, total):
    """
    Return N items from values.
    >>> sampling(range(10), 5)
    [0, 2, 4, 6, 8]
    >>> sampling('abcdefghijkl', 4)
    ['a', 'd', 'g', 'j']
    """
    step = max(1, int(len(values) / total))
    return list(islice(values, 0, len(values), step))


def uniquify(values):
    """
    Return unique values, order preserved
    """
    unique = []
    [unique.append(i) for i in values if i not in unique]
    return unique


def intersecting(cls, obj, distance=None):
    """ Small helper to filter all model instances by geometry intersection
    """
    if distance:
        qs = cls.objects.filter(geom__dwithin=(obj.geom, Distance(m=distance)))
    else:
        qs = cls.objects.filter(geom__intersects=obj.geom)
    if obj.__class__ == cls:
        # Prevent self intersection
        qs = qs.exclude(pk=obj.pk)
    return qs
