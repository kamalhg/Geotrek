# -*- coding: utf-8 -*-
import json
import logging

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import last_modified as cache_last_modified
from django.views.decorators.cache import never_cache as force_cache_validation
from django.core.cache import get_cache
from django.shortcuts import redirect
from mapentity.views import (MapEntityLayer, MapEntityList, MapEntityJsonList,
                             MapEntityDetail, MapEntityDocument, MapEntityCreate, MapEntityUpdate,
                             MapEntityDelete, MapEntityFormat,
                             HttpJSONResponse)

from geotrek.authent.decorators import same_structure_required
from geotrek.common.utils import classproperty

from .models import Path, Trail, Topology
from .forms import PathForm, TrailForm
from .filters import PathFilterSet, TrailFilterSet
from . import graph as graph_lib


logger = logging.getLogger(__name__)


@login_required
def last_list(request):
    last = request.session.get('last_list')  # set in MapEntityList
    if not last:
        return redirect('core:path_list')
    return redirect(last)

home = last_list


class CreateFromTopologyMixin(object):
    def on_topology(self):
        pk = self.request.GET.get('topology')
        if pk:
            try:
                return Topology.objects.existing().get(pk=pk)
            except Topology.DoesNotExist:
                logger.warning("Intervention on unknown topology %s" % pk)
        return None

    def get_initial(self):
        initial = super(CreateFromTopologyMixin, self).get_initial()
        # Create intervention with an existing topology as initial data
        topology = self.on_topology()
        if topology:
            initial['topology'] = topology.serialize(with_pk=False)
        return initial


class PathLayer(MapEntityLayer):
    model = Path
    properties = ['name']


class PathList(MapEntityList):
    queryset = Path.objects.prefetch_related('networks').select_related('stake')
    filterform = PathFilterSet

    @classproperty
    def columns(cls):
        columns = ['id', 'name', 'networks', 'length']
        if settings.TRAIL_MODEL_ENABLED:
            columns.append('trails')
        return columns

    def get_queryset(self):
        """
        denormalize ``trail`` column from list.
        """
        qs = super(PathList, self).get_queryset()

        denormalized = {}
        if settings.TRAIL_MODEL_ENABLED:
            paths_id = qs.values_list('id', flat=True)
            paths_trails = Trail.objects.filter(aggregations__path__id__in=paths_id)
            by_id = dict([(trail.id, trail) for trail in paths_trails])
            trails_paths_ids = paths_trails.values_list('id', 'aggregations__path__id')
            for trail_id, path_id in trails_paths_ids:
                denormalized.setdefault(path_id, []).append(by_id[trail_id])

        for path in qs:
            path_trails = denormalized.get(path.id, [])
            setattr(path, '_trails', path_trails)
            yield path


class PathJsonList(MapEntityJsonList, PathList):
    pass


class PathFormatList(MapEntityFormat, PathList):
    pass


class PathDetail(MapEntityDetail):
    model = Path

    def context_data(self, *args, **kwargs):
        context = super(PathDetail, self).context_data(*args, **kwargs)
        context['can_edit'] = self.get_object().same_structure(self.request.user)
        return context


class PathDocument(MapEntityDocument):
    model = Path

    def get_context_data(self, *args, **kwargs):
        self.get_object().prepare_elevation_chart(self.request.build_absolute_uri('/'))
        return super(PathDocument, self).get_context_data(*args, **kwargs)


class PathCreate(MapEntityCreate):
    model = Path
    form_class = PathForm


class PathUpdate(MapEntityUpdate):
    model = Path
    form_class = PathForm

    @same_structure_required('core:path_detail')
    def dispatch(self, *args, **kwargs):
        return super(PathUpdate, self).dispatch(*args, **kwargs)


class PathDelete(MapEntityDelete):
    model = Path

    @same_structure_required('core:path_detail')
    def dispatch(self, *args, **kwargs):
        return super(PathDelete, self).dispatch(*args, **kwargs)


@login_required
@cache_last_modified(lambda x: Path.latest_updated())
@force_cache_validation
def get_graph_json(request):
    cache = get_cache('fat')
    key = 'path_graph_json'

    result = cache.get(key)
    latest = Path.latest_updated()

    if result and latest:
        cache_latest, json_graph = result
        # Not empty and still valid
        if cache_latest and cache_latest >= latest:
            return HttpJSONResponse(json_graph)

    # cache does not exist or is not up to date
    # rebuild the graph and cache the json
    graph = graph_lib.graph_edges_nodes_of_qs(Path.objects.all())
    json_graph = json.dumps(graph)

    cache.set(key, (latest, json_graph))
    return HttpJSONResponse(json_graph)


class TrailLayer(MapEntityLayer):
    queryset = Trail.objects.existing()
    properties = ['name']


class TrailList(MapEntityList):
    queryset = Trail.objects.existing()
    filterform = TrailFilterSet
    columns = ['id', 'name', 'departure', 'arrival', 'length']


class TrailDetail(MapEntityDetail):
    queryset = Trail.objects.existing()

    def context_data(self, *args, **kwargs):
        context = super(TrailDetail, self).context_data(*args, **kwargs)
        context['can_edit'] = self.get_object().same_structure(self.request.user)
        return context


class TrailDocument(MapEntityDocument):
    queryset = Trail.objects.existing()


class TrailCreate(CreateFromTopologyMixin, MapEntityCreate):
    model = Trail
    form_class = TrailForm


class TrailUpdate(MapEntityUpdate):
    queryset = Trail.objects.existing()
    form_class = TrailForm

    @same_structure_required('core:trail_detail')
    def dispatch(self, *args, **kwargs):
        return super(TrailUpdate, self).dispatch(*args, **kwargs)


class TrailDelete(MapEntityDelete):
    queryset = Trail.objects.existing()

    @same_structure_required('core:trail_detail')
    def dispatch(self, *args, **kwargs):
        return super(TrailDelete, self).dispatch(*args, **kwargs)
