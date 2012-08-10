from django.contrib.gis.geos import Point, LineString

import floppyforms as forms
from crispy_forms.layout import Field

from caminae.core.forms import MapEntityForm
from caminae.core.widgets import PointOrMultipathWidget

from .models import Intervention


class InterventionForm(MapEntityForm):
    geom = forms.gis.GeometryField(widget=PointOrMultipathWidget)

    modelfields = (
            'name',
            'structure',
            'date',
            'status',
            'typology',
            'disorders',
            Field('comments', css_class='input-xlarge'),
            'in_maintenance',
            'length',
            'height',
            'width',
            'area',
            'slope',
            'material_cost',
            'heliport_cost',
            'subcontract_cost',
            'stake',
            'project',)
    geomfields = ('geom',)

    def save(self, commit=True):
        intervention = super(InterventionForm, self).save(commit)
        if not commit:
            return intervention
        
        geom = self.cleaned_data.get('geom')
        if not geom:
            pass  # raise ValueError !

        if isinstance(geom, Point):
            intervention.initFromPoint(geom)
        elif isinstance(geom, LineString):
            # TODO: later it should be list of Path objects (from list of pks in form)
            intervention.initFromPathsList(geom)
        return intervention

    class Meta:
        model = Intervention
        exclude = ('deleted', 'topology', 'jobs')  # TODO