import factory
from django.contrib.gis.geos import Point, LineString
from django.conf import settings

from caminae.authent.factories import StructureRelatedDefaultFactory
from caminae.common.utils import dbnow
from . import models


class DatasourceFactory(factory.Factory):
    FACTORY_FOR = models.Datasource

    source = factory.Sequence(lambda n: u"Datasource %s" % n)


class StakeFactory(factory.Factory):
    FACTORY_FOR = models.Stake

    stake = factory.Sequence(lambda n: u"Stake %s" % n)


class UsageFactory(factory.Factory):
    FACTORY_FOR = models.Usage

    usage = factory.Sequence(lambda n: u"Usage %s" % n)


class NetworkFactory(factory.Factory):
    FACTORY_FOR = models.Network

    network = factory.Sequence(lambda n: u"Network %s" % n)


class TrailFactory(factory.Factory):
    FACTORY_FOR = models.Trail

    name =  factory.Sequence(lambda n: u"Name %s" % n)
    departure =  factory.Sequence(lambda n: u"Departure %s" % n)
    arrival =  factory.Sequence(lambda n: u"Arrival %s" % n)
    comments =  factory.Sequence(lambda n: u"Comments %s" % n)


class PathFactory(StructureRelatedDefaultFactory):
    FACTORY_FOR = models.Path

    geom = LineString(Point(1, 1, 0), Point(2, 2, 0), srid=settings.SRID)
    geom_cadastre = LineString(Point(5, 5, 0), Point(6, 6, 0), srid=settings.SRID)
    valid = True
    name = factory.Sequence(lambda n: u"name %s" % n)
    comments = factory.Sequence(lambda n: u"comment %s" % n)

    # Trigger will override :
    date_insert = dbnow()
    date_update = dbnow()
    length = 0.0
    ascent = 0
    descent = 0
    min_elevation = 0
    max_elevation = 0

    # FK that could also be null
    trail = factory.SubFactory(TrailFactory)
    datasource = factory.SubFactory(DatasourceFactory)
    stake = factory.SubFactory(StakeFactory)


class TopologyMixinKindFactory(factory.Factory):
    FACTORY_FOR = models.TopologyMixinKind

    kind = factory.Sequence(lambda n: u"Kind %s" % n)


class TopologyMixinFactory(factory.Factory):
    FACTORY_FOR = models.TopologyMixin

    # Factory
    # troncons (M2M)
    offset = 0
    deleted = False
    kind = factory.SubFactory(TopologyMixinKindFactory)

    # Trigger will override :
    date_insert = dbnow()
    date_update = dbnow()

    @classmethod
    def _prepare(cls, create, **kwargs):
        """
        A topology mixin should be linked to at least one Path (through
        PathAggregation).
        """

        no_path = kwargs.pop('no_path', False)
        topo_mixin = super(TopologyMixinFactory, cls)._prepare(create, **kwargs)

        if not no_path and create:
            PathAggregationFactory.create(topo_object=topo_mixin)
            # Note that it is not possible to attach a related object before the
            # topo_mixin has an ID.
        return topo_mixin


class PathAggregationFactory(factory.Factory):
    FACTORY_FOR = models.PathAggregation

    path = factory.SubFactory(PathFactory)
    topo_object = factory.SubFactory(TopologyMixinFactory)

    start_position = 0.0
    end_position = 1.0
