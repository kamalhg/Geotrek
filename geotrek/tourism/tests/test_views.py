# -*- coding: utf-8 -*-
import os
import json

import mock
from requests.exceptions import ConnectionError
from django.contrib.auth.models import Group
from django.core.urlresolvers import reverse
from django.conf import settings
from django.test.utils import override_settings

from geotrek.authent.factories import StructureFactory, UserProfileFactory
from geotrek.authent.tests.base import AuthentFixturesTest
from geotrek.trekking.tests import TrekkingManagerTest
from geotrek.core import factories as core_factories
from geotrek.trekking import factories as trekking_factories
from geotrek.zoning import factories as zoning_factories
from geotrek.common import factories as common_factories
from geotrek.common.utils.testdata import get_dummy_uploaded_image
from geotrek.tourism.models import DATA_SOURCE_TYPES
from geotrek.tourism.factories import (DataSourceFactory,
                                       InformationDeskFactory,
                                       TouristicContentFactory,
                                       TouristicEventFactory,
                                       TouristicContentCategoryFactory,
                                       TouristicContentTypeFactory)


class TourismAdminViewsTests(TrekkingManagerTest):

    def setUp(self):
        self.source = DataSourceFactory.create()
        self.login()

    def test_trekking_managers_can_access_data_sources_admin_site(self):
        url = reverse('admin:tourism_datasource_changelist')
        response = self.client.get(url)
        self.assertContains(response, 'datasource/%s' % self.source.id)

    def test_datasource_title_is_translated(self):
        url = reverse('admin:tourism_datasource_add')
        response = self.client.get(url)
        self.assertContains(response, 'title_fr')


class DataSourceListViewTests(TrekkingManagerTest):
    def setUp(self):
        self.source = DataSourceFactory.create(title_it='titolo')
        self.login()
        self.url = reverse('tourism:datasource_list_json')
        self.response = self.client.get(self.url)

    def tearDown(self):
        self.client.logout()

    def test_sources_are_listed_as_json(self):
        self.assertEqual(self.response.status_code, 200)
        self.assertEqual(self.response['Content-Type'], 'application/json')

    def test_sources_properties_are_provided(self):
        datasources = json.loads(self.response.content)
        self.assertEqual(len(datasources), 1)
        self.assertEqual(datasources[0]['id'], self.source.id)
        self.assertEqual(datasources[0]['url'], self.source.url)

    def test_sources_respect_request_language(self):
        response = self.client.get(self.url, HTTP_ACCEPT_LANGUAGE='it-IT')
        self.assertEqual(response.status_code, 200)
        datasources = json.loads(response.content)
        self.assertEqual(datasources[0]['title'],
                         self.source.title_it)

    def test_sources_provide_geojson_absolute_url(self):
        datasources = json.loads(self.response.content)
        self.assertEqual(datasources[0]['geojson_url'],
                         u'/api/datasource/datasource-%s.geojson' % self.source.id)


class DataSourceViewTests(TrekkingManagerTest):
    def setUp(self):
        self.source = DataSourceFactory.create(type=DATA_SOURCE_TYPES.GEOJSON)
        self.url = reverse('tourism:datasource_geojson', kwargs={'pk': self.source.pk})
        self.login()

    def tearDown(self):
        self.client.logout()

    def test_source_is_fetched_upon_view_call(self):
        with mock.patch('requests.get') as mocked:
            mocked().text = '{}'
            self.client.get(self.url)
            mocked.assert_called_with(self.source.url)

    def test_empty_source_response_return_empty_data(self):
        with mock.patch('requests.get') as mocked:
            mocked().text = '{}'
            response = self.client.get(self.url)
            self.assertEqual(response.status_code, 200)
            datasource = json.loads(response.content)
            self.assertEqual(datasource['features'], [])

    def test_source_is_returned_as_geojson_when_invalid_geojson(self):
        with mock.patch('requests.get') as mocked:
            mocked().text = '{"bar": "foo"}'
            response = self.client.get(self.url)
            geojson = json.loads(response.content)
            self.assertEqual(geojson['type'], 'FeatureCollection')
            self.assertEqual(geojson['features'], [])

    def test_source_is_returned_as_geojson_when_invalid_response(self):
        with mock.patch('requests.get') as mocked:
            mocked().text = '404 page not found'
            response = self.client.get(self.url)
            geojson = json.loads(response.content)
            self.assertEqual(geojson['type'], 'FeatureCollection')
            self.assertEqual(geojson['features'], [])

    def test_source_is_returned_as_geojson_when_network_problem(self):
        with mock.patch('requests.get') as mocked:
            mocked.side_effect = ConnectionError
            response = self.client.get(self.url)
            geojson = json.loads(response.content)
            self.assertEqual(geojson['type'], 'FeatureCollection')
            self.assertEqual(geojson['features'], [])


class DataSourceTourInFranceViewTests(TrekkingManagerTest):
    def setUp(self):
        here = os.path.dirname(__file__)
        filename = os.path.join(here, 'data', 'sit-averyon-02.01.14.xml')
        self.sample = open(filename).read()

        self.source = DataSourceFactory.create(type=DATA_SOURCE_TYPES.TOURINFRANCE)
        self.url = reverse('tourism:datasource_geojson', kwargs={'pk': self.source.pk})
        self.login()

    def tearDown(self):
        self.client.logout()

    def test_source_is_returned_as_geojson_when_tourinfrance(self):
        with mock.patch('requests.get') as mocked:
            mocked().text = "<xml></xml>"
            response = self.client.get(self.url)
            geojson = json.loads(response.content)
            self.assertEqual(geojson['type'], 'FeatureCollection')

    def test_source_is_returned_in_language_request(self):
        with mock.patch('requests.get') as mocked:
            mocked().text = self.sample
            response = self.client.get(self.url, HTTP_ACCEPT_LANGUAGE='es-ES')
            geojson = json.loads(response.content)
            feature = geojson['features'][0]
            self.assertEqual(feature['properties']['description'],
                             u'Ubicada en la región minera del Aveyron, nuestra casa rural os permitirá decubrir la naturaleza y el patrimonio industrial de la cuenca de Aubin y Decazeville.')


class DataSourceSitraViewTests(TrekkingManagerTest):
    def setUp(self):
        here = os.path.dirname(__file__)
        filename = os.path.join(here, 'data', 'sitra-multilang-10.06.14.json')
        self.sample = open(filename).read()

        self.source = DataSourceFactory.create(type=DATA_SOURCE_TYPES.SITRA)
        self.url = reverse('tourism:datasource_geojson', kwargs={'pk': self.source.pk})
        self.login()

    def tearDown(self):
        self.client.logout()

    def test_source_is_returned_as_geojson_when_sitra(self):
        with mock.patch('requests.get') as mocked:
            mocked().text = "{}"
            response = self.client.get(self.url)
            geojson = json.loads(response.content)
            self.assertEqual(geojson['type'], 'FeatureCollection')

    def test_source_is_returned_in_language_request(self):
        with mock.patch('requests.get') as mocked:
            mocked().text = self.sample
            response = self.client.get(self.url, HTTP_ACCEPT_LANGUAGE='es-ES')
            geojson = json.loads(response.content)
            feature = geojson['features'][0]
            self.assertEqual(feature['properties']['title'],
                             u'Refugios en Valgaudemar')

    def test_default_language_is_returned_when_not_available(self):
        with mock.patch('requests.get') as mocked:
            mocked().text = self.sample
            response = self.client.get(self.url, HTTP_ACCEPT_LANGUAGE='es-ES')
            geojson = json.loads(response.content)
            feature = geojson['features'][0]
            self.assertEqual(feature['properties']['description'],
                             u"Randonnée idéale pour bons marcheurs, une immersion totale dans la vallée du Valgaudemar, au coeur du territoire préservé du Parc national des Ecrins. Un grand voyage ponctué d'étapes en altitude, avec une ambiance chaleureuse dans les refuges du CAF.")

    def test_website_can_be_obtained(self):
        with mock.patch('requests.get') as mocked:
            mocked().text = self.sample
            response = self.client.get(self.url, HTTP_ACCEPT_LANGUAGE='es-ES')
            geojson = json.loads(response.content)
            feature = geojson['features'][0]
            self.assertEqual(feature['properties']['website'],
                             "http://www.cirkwi.com/#!page=circuit&id=12519&langue=fr")

    def test_phone_can_be_obtained(self):
        with mock.patch('requests.get') as mocked:
            mocked().text = self.sample
            response = self.client.get(self.url, HTTP_ACCEPT_LANGUAGE='es-ES')
            geojson = json.loads(response.content)
            feature = geojson['features'][0]
            self.assertEqual(feature['properties']['phone'],
                             "04 92 55 23 21")

    def test_geometry_as_geojson(self):
        with mock.patch('requests.get') as mocked:
            mocked().text = self.sample
            response = self.client.get(self.url, HTTP_ACCEPT_LANGUAGE='es-ES')
            geojson = json.loads(response.content)
            feature = geojson['features'][0]
            self.assertDictEqual(feature['geometry'],
                                 {"type": "Point",
                                  "coordinates": [6.144058, 44.826552]})

    def test_list_of_pictures(self):
        with mock.patch('requests.get') as mocked:
            mocked().text = self.sample
            response = self.client.get(self.url, HTTP_ACCEPT_LANGUAGE='es-ES')
            geojson = json.loads(response.content)
            feature = geojson['features'][0]
            self.assertDictEqual(feature['properties']['pictures'][0],
                                 {u'copyright': u'Christian Martelet',
                                  u'legend': u'Refuges en Valgaudemar',
                                  u'url': u'http://static.sitra-tourisme.com/filestore/objets-touristiques/images/600938.jpg'})


class InformationDeskViewsTests(TrekkingManagerTest):
    def setUp(self):
        InformationDeskFactory.create_batch(size=10)
        self.url = reverse('tourism:informationdesk_geojson')
        self.login()

    def tearDown(self):
        self.client.logout()

    def test_geojson_layer_of_all_information_desks(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        records = json.loads(response.content)
        self.assertEqual(len(records['features']), 10)


class TouristicContentViewsSameStructureTests(AuthentFixturesTest):
    def setUp(self):
        profile = UserProfileFactory.create(user__username='homer',
                                            user__password='dooh')
        user = profile.user
        user.groups.add(Group.objects.get(name=u"Référents communication"))
        self.client.login(username=user.username, password='dooh')
        self.content1 = TouristicContentFactory.create()
        structure = StructureFactory.create()
        self.content2 = TouristicContentFactory.create(structure=structure)

    def test_can_edit_same_structure(self):
        url = "/touristiccontent/edit/{pk}/".format(pk=self.content1.pk)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_cannot_edit_other_structure(self):
        url = "/touristiccontent/edit/{pk}/".format(pk=self.content2.pk)
        response = self.client.get(url)
        self.assertRedirects(response, "/touristiccontent/{pk}/".format(pk=self.content2.pk))

    def test_can_delete_same_structure(self):
        url = "/touristiccontent/delete/{pk}/".format(pk=self.content1.pk)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_cannot_delete_other_structure(self):
        url = "/touristiccontent/delete/{pk}/".format(pk=self.content2.pk)
        response = self.client.get(url)
        self.assertRedirects(response, "/touristiccontent/{pk}/".format(pk=self.content2.pk))


class TouristicContentTemplatesTest(TrekkingManagerTest):
    def setUp(self):
        self.content = TouristicContentFactory.create()
        cat = self.content.category
        cat.type1_label = 'Michelin'
        cat.save()
        self.category2 = TouristicContentCategoryFactory()
        self.login()

    def tearDown(self):
        self.client.logout()

    def test_only_used_categories_are_shown(self):
        url = "/touristiccontent/list/"
        response = self.client.get(url)
        self.assertContains(response, 'title="%s"' % self.content.category.label)
        self.assertNotContains(response, 'title="%s"' % self.category2.label)

    def test_shown_in_details_when_enabled(self):
        url = "/touristiccontent/%s/" % self.content.pk
        response = self.client.get(url)
        self.assertContains(response, 'Tourism')

    @override_settings(TOURISM_ENABLED=False)
    def test_not_shown_in_details_when_disabled(self):
        url = "/touristiccontent/%s/" % self.content.pk
        response = self.client.get(url)
        self.assertNotContains(response, 'Tourism')

    def test_type_label_shown_in_detail_page(self):
        url = "/touristiccontent/{pk}/".format(pk=self.content.pk)
        response = self.client.get(url)
        self.assertContains(response, 'Michelin')


class TouristicContentCategoryListTest(TrekkingManagerTest):
    def setUp(self):
        self.category = TouristicContentCategoryFactory.create()
        TouristicContentCategoryFactory.create()
        self.login()

    def test_categories_are_published_in_json(self):
        url = "/api/touristiccontent/categories/"
        response = self.client.get(url)
        results = json.loads(response.content)
        self.assertEqual(results[0]['label'], self.category.label)
        self.assertIn('types', results[0])


class TouristicContentFormTest(TrekkingManagerTest):
    def setUp(self):
        self.category = TouristicContentCategoryFactory()
        self.login()

    def test_no_category_selected_by_default(self):
        url = "/touristiccontent/add/"
        response = self.client.get(url)
        self.assertNotContains(response, 'value="%s" selected' % self.category.pk)

    def test_default_category_is_taken_from_url_params(self):
        url = "/touristiccontent/add/?category=%s" % self.category.pk
        response = self.client.get(url)
        self.assertContains(response, 'value="%s" selected' % self.category.pk)


class BasicJSONAPITest(object):
    factory = None

    def setUp(self):
        self.login()

        self._build_object()

        self.pk = self.content.pk
        url = '/api/%ss/%s/' % (self.content._meta.module_name, self.pk)
        self.response = self.client.get(url)
        self.result = json.loads(self.response.content)

    def _build_object(self):
        polygon = 'SRID=%s;MULTIPOLYGON(((0 0, 0 3, 3 3, 3 0, 0 0)))' % settings.SRID
        self.city = zoning_factories.CityFactory(geom=polygon)
        self.district = zoning_factories.DistrictFactory(geom=polygon)

        self.content = self.factory(geom='SRID=%s;POINT(1 1)' % settings.SRID)

        self.attachment = common_factories.AttachmentFactory(obj=self.content,
                                                             attachment_file=get_dummy_uploaded_image())
        self.theme = common_factories.ThemeFactory()
        self.content.themes.add(self.theme)

        path = core_factories.PathFactory(geom='SRID=%s;LINESTRING(0 10, 10 10)' % settings.SRID)
        self.trek = trekking_factories.TrekFactory(no_path=True)
        self.trek.add_path(path)
        self.poi = trekking_factories.POIFactory(no_path=True)
        self.poi.add_path(path, start=0.5, end=0.5)

    def test_thumbnail(self):
        self.assertEqual(self.result['thumbnail'],
                         os.path.join(settings.MEDIA_URL, self.attachment.attachment_file.name) + '.120x120_q85_crop.png')

    def test_published_status(self):
        self.assertDictEqual(self.result['published_status'][0],
                             {u'lang': u'en', u'status': False, u'language': u'English'})

    def test_pictures(self):
        self.assertDictEqual(self.result['pictures'][0],
                             {u'url': os.path.join(settings.MEDIA_URL, self.attachment.attachment_file.name) + '.800x800_q85.png',
                              u'title': self.attachment.title,
                              u'legend': self.attachment.legend,
                              u'author': self.attachment.author})

    def test_cities(self):
        self.assertDictEqual(self.result['cities'][0],
                             {u"code": self.city.code,
                              u"name": self.city.name})

    def test_districts(self):
        self.assertDictEqual(self.result['districts'][0],
                             {u"id": self.district.id,
                              u"name": self.district.name})

    def test_themes(self):
        self.assertDictEqual(self.result['themes'][0],
                             {u"id": self.theme.id,
                              u"pictogram": os.path.join(settings.MEDIA_URL, self.theme.pictogram.name),
                              u"label": self.theme.label})

    def test_treks(self):
        self.assertDictEqual(self.result['treks'][0], {
            u'pk': self.trek.pk,
            u'id': self.trek.id,
            u'slug': self.trek.slug,
            u'name': self.trek.name,
            u'url': u'/trek/%s/' % self.trek.id})

    def test_pois(self):
        self.assertDictEqual(self.result['pois'][0], {
            u'id': self.poi.id,
            u'slug': self.poi.slug,
            u'name': self.poi.name,
            u'type': {
                u'id': self.poi.type.id,
                u'label': self.poi.type.label,
                u'pictogram': os.path.join(settings.MEDIA_URL, self.poi.type.pictogram.name)}})


class TouristicContentAPITest(BasicJSONAPITest, TrekkingManagerTest):
    factory = TouristicContentFactory

    def _build_object(self):
        super(TouristicContentAPITest, self)._build_object()
        self.category = self.content.category
        self.type1 = TouristicContentTypeFactory(category=self.category)
        self.type2 = TouristicContentTypeFactory(category=self.category)
        self.content.type1.add(self.type1)
        self.content.type2.add(self.type2)

    def test_expected_properties(self):
        self.assertEqual([
            'areas', 'category', 'cities', 'contact',
            'description', 'description_teaser', 'districts', 'email',
            'filelist_url', 'id', 'map_image_url', 'name', 'pictures', 'pois',
            'practical_info', 'printable', 'publication_date', 'published',
            'published_status', 'slug', 'themes', 'thumbnail',
            'touristic_contents', 'touristic_events', 'treks',
            'type1', 'type2', 'website'],
            sorted(self.result.keys()))

    def test_type1(self):
        self.assertDictEqual(self.result['type1'][0],
                             {u"id": self.type1.id,
                              u"name": self.type1.label,
                              u"in_list": self.type1.in_list})

    def test_type2(self):
        self.assertDictEqual(self.result['type2'][0],
                             {u"id": self.type2.id,
                              u"name": self.type2.label,
                              u"in_list": self.type2.in_list})

    def test_category(self):
        self.assertDictEqual(self.result['category'], {
            u"id": self.category.id,
            u"types": [
                {u"id": self.type1.id,
                 u"name": self.type1.label,
                 u"in_list": self.type1.in_list},
                {u"id": self.type2.id,
                 u"name": self.type2.label,
                 u"in_list": self.type2.in_list}
            ],
            "label": self.category.label,
            "type1_label": self.category.type1_label,
            "type2_label": self.category.type2_label,
            "pictogram": os.path.join(settings.MEDIA_URL, self.category.pictogram.name)})


class TouristicEventAPITest(BasicJSONAPITest, TrekkingManagerTest):
    factory = TouristicEventFactory

    def test_expected_properties(self):
        self.assertEqual([
            'accessibility', 'areas', 'begin_date', 'booking',
            'cities', 'contact', 'description', 'description_teaser',
            'districts', 'duration', 'email', 'end_date', 'filelist_url',
            'id', 'map_image_url', 'meeting_point', 'meeting_time', 'name',
            'organizer', 'participant_number', 'pictures', 'pois', 'practical_info',
            'printable', 'public', 'publication_date', 'published', 'published_status',
            'slug', 'speaker', 'themes', 'thumbnail',
            'touristic_contents', 'touristic_events', 'treks', 'type', 'website'],
            sorted(self.result.keys()))

    def test_type(self):
        self.assertDictEqual(self.result['type'],
                             {u"id": self.content.type.id,
                              u"name": self.content.type.type})

    def test_public(self):
        self.assertDictEqual(self.result['public'],
                             {u"id": self.content.public.id,
                              u"name": self.content.public.public})


class TouristicEventViewsSameStructureTests(AuthentFixturesTest):
    def setUp(self):
        profile = UserProfileFactory.create(user__username='homer',
                                            user__password='dooh')
        user = profile.user
        user.groups.add(Group.objects.get(name=u"Référents communication"))
        self.client.login(username=user.username, password='dooh')
        self.event1 = TouristicEventFactory.create()
        structure = StructureFactory.create()
        self.event2 = TouristicEventFactory.create(structure=structure)

    def test_can_edit_same_structure(self):
        url = "/touristicevent/edit/{pk}/".format(pk=self.event1.pk)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_cannot_edit_other_structure(self):
        url = "/touristicevent/edit/{pk}/".format(pk=self.event2.pk)
        response = self.client.get(url)
        self.assertRedirects(response, "/touristicevent/{pk}/".format(pk=self.event2.pk))

    def test_can_delete_same_structure(self):
        url = "/touristicevent/delete/{pk}/".format(pk=self.event1.pk)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_cannot_delete_other_structure(self):
        url = "/touristicevent/delete/{pk}/".format(pk=self.event2.pk)
        response = self.client.get(url)
        self.assertRedirects(response, "/touristicevent/{pk}/".format(pk=self.event2.pk))
