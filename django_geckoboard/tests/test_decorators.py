"""
Tests for the Geckoboard decorators.
"""

import simplejson
from django.http import HttpRequest, HttpResponseForbidden
from django.utils.datastructures import SortedDict

from django_geckoboard.decorators import widget, number_widget, rag_widget, \
        text_widget, pie_chart, line_chart, geck_o_meter, TEXT_NONE, \
        TEXT_INFO, TEXT_WARN, funnel, bullet
from django_geckoboard.tests.utils import TestCase
import base64


class WidgetDecoratorTestCase(TestCase):
    """
    Tests for the ``widget`` decorator.
    """

    def setUp(self):
        super(WidgetDecoratorTestCase, self).setUp()
        self.settings_manager.delete('GECKOBOARD_API_KEY')
        self.xml_request = HttpRequest()
        self.xml_request.POST['format'] = '1'
        self.json_request = HttpRequest()
        self.json_request.POST['format'] = '2'

    def test_api_key(self):
        self.settings_manager.set(GECKOBOARD_API_KEY='abc')
        req = HttpRequest()
        req.META['HTTP_AUTHORIZATION'] = "basic %s" % base64.b64encode('abc')
        resp = widget(lambda r: "test")(req)
        self.assertEqual('<?xml version="1.0" ?><root>test</root>',
                resp.content)

    def test_missing_api_key(self):
        self.settings_manager.set(GECKOBOARD_API_KEY='abc')
        req = HttpRequest()
        resp = widget(lambda r: "test")(req)
        self.assertTrue(isinstance(resp, HttpResponseForbidden), resp)
        self.assertEqual('Geckoboard API key incorrect', resp.content)

    def test_wrong_api_key(self):
        self.settings_manager.set(GECKOBOARD_API_KEY='abc')
        req = HttpRequest()
        req.META['HTTP_AUTHORIZATION'] = "basic %s" % base64.b64encode('def')
        resp = widget(lambda r: "test")(req)
        self.assertTrue(isinstance(resp, HttpResponseForbidden), resp)
        self.assertEqual('Geckoboard API key incorrect', resp.content)

    def test_xml_get(self):
        req = HttpRequest()
        req.GET['format'] = '1'
        resp = widget(lambda r: "test")(req)
        self.assertEqual('<?xml version="1.0" ?><root>test</root>',
                resp.content)
        self.assertEqual(resp._headers['content-type'], ('Content-Type', 'application/xml'))

    def test_json_get(self):
        req = HttpRequest()
        req.GET['format'] = '2'
        resp = widget(lambda r: "test")(req)
        self.assertEqual('"test"', resp.content)
        self.assertEqual(resp._headers['content-type'], ('Content-Type', 'application/json'))

    def test_encrypted_json_get(self):
        req = HttpRequest()
        req.GET['format'] = '2'
        resp = widget(encrypted=True)(lambda r: "test")(req)
        self.assertNotEqual('"test"', resp.content)
        self.assertEqual(44, len(resp.content))
        self.assertEqual(resp._headers['content-type'], ('Content-Type', 'application/json'))

    def test_xml_post(self):
        req = HttpRequest()
        req.POST['format'] = '1'
        resp = widget(lambda r: "test")(req)
        self.assertEqual('<?xml version="1.0" ?><root>test</root>',
                resp.content)
        self.assertEqual(resp._headers['content-type'], ('Content-Type', 'application/xml'))

    def test_json_post(self):
        req = HttpRequest()
        req.POST['format'] = '2'
        resp = widget(lambda r: "test")(req)
        self.assertEqual('"test"', resp.content)
        self.assertEqual(resp._headers['content-type'], ('Content-Type', 'application/json'))

    def test_scalar_xml(self):
        resp = widget(lambda r: "test")(self.xml_request)
        self.assertEqual('<?xml version="1.0" ?><root>test</root>',
                resp.content)

    def test_scalar_json(self):
        resp = widget(lambda r: "test")(self.json_request)
        self.assertEqual('"test"', resp.content)

    def test_dict_xml(self):
        resp = widget(lambda r: SortedDict([('a', 1),
                ('b', 2)]))(self.xml_request)
        self.assertEqual('<?xml version="1.0" ?><root><a>1</a><b>2</b></root>',
                resp.content)

    def test_dict_json(self):
        resp = widget(lambda r: SortedDict([('a', 1),
                ('b', 2)]))(self.json_request)
        self.assertEqual('{"a": 1, "b": 2}', resp.content)

    def test_list_xml(self):
        resp = widget(lambda r: {'list': [1, 2, 3]})(self.xml_request)
        self.assertEqual('<?xml version="1.0" ?><root><list>1</list>'
                '<list>2</list><list>3</list></root>', resp.content)

    def test_list_json(self):
        resp = widget(lambda r: {'list': [1, 2, 3]})(self.json_request)
        self.assertEqual('{"list": [1, 2, 3]}', resp.content)

    def test_dict_list_xml(self):
        resp = widget(lambda r: {'item': [{'value': 1, 'text': "test1"},
                {'value': 2, 'text': "test2"}]})(self.xml_request)
        self.assertEqual('<?xml version="1.0" ?><root>'
                '<item><text>test1</text><value>1</value></item>'
                '<item><text>test2</text><value>2</value></item></root>',
                resp.content)

    def test_dict_list_json(self):
        resp = widget(lambda r: {'item': [SortedDict([('value', 1),
                ('text', "test1")]), SortedDict([('value', 2), ('text',
                        "test2")])]})(self.json_request)
        self.assertEqual('{"item": [{"value": 1, "text": "test1"}, '
                '{"value": 2, "text": "test2"}]}', resp.content)


class NumberDecoratorTestCase(TestCase):
    """
    Tests for the ``number`` decorator.
    """

    def setUp(self):
        super(NumberDecoratorTestCase, self).setUp()
        self.settings_manager.delete('GECKOBOARD_API_KEY')
        self.request = HttpRequest()
        self.request.POST['format'] = '2'

    def test_scalar(self):
        widget = number_widget(lambda r: 10)
        resp = widget(self.request)
        self.assertEqual('{"item": [{"value": 10}]}', resp.content)

    def test_singe_value(self):
        widget = number_widget(lambda r: [10])
        resp = widget(self.request)
        self.assertEqual('{"item": [{"value": 10}]}', resp.content)

    def test_single_value_and_parameter(self):
        widget = number_widget(absolute='true')(lambda r: [10])
        resp = widget(self.request)
        json = '{"item": [{"value": 10}], "absolute": "true"}'
        self.assertEqual(json, resp.content)

    def test_single_value_as_dictionary(self):
        widget = number_widget(lambda r: [{'value': 10}])
        resp = widget(self.request)
        json = '{"item": [{"value": 10}]}'
        self.assertEqual(json, resp.content)

    def test_single_value_as_dictionary_with_prefix(self):
        widget = number_widget(lambda r: [{'value': 10, 'prefix': '$'}])
        resp = widget(self.request)
        json = '{"item": [{"prefix": "$", "value": 10}]}'
        self.assertEqual(json, resp.content)

    def test_two_values(self):
        widget = number_widget(lambda r: [10, 9])
        resp = widget(self.request)
        self.assertEqual('{"item": [{"value": 10}, {"value": 9}]}',
                resp.content)

    def test_two_values_and_parameter(self):
        widget = number_widget(absolute='true')(lambda r: [10, 9])
        resp = widget(self.request)
        json = '{"item": [{"value": 10}, {"value": 9}], "absolute": "true"}'
        self.assertEqual(json, resp.content)

    def test_two_values_as_dictionary(self):
        widget = number_widget(lambda r: [{'value': 10}, {'value': 9}])
        resp = widget(self.request)
        json = '{"item": [{"value": 10}, {"value": 9}]}'
        self.assertEqual(json, resp.content)

    def test_two_values_as_dictionary_with_prefix(self):
        widget = number_widget(lambda r: [{'value': 10, 'prefix': '$'}, {'value': 9}])
        resp = widget(self.request)
        json = '{"item": [{"prefix": "$", "value": 10}, {"value": 9}]}'
        self.assertEqual(json, resp.content)


class RAGDecoratorTestCase(TestCase):
    """
    Tests for the ``rag`` decorator.
    """

    def setUp(self):
        super(RAGDecoratorTestCase, self).setUp()
        self.settings_manager.delete('GECKOBOARD_API_KEY')
        self.request = HttpRequest()
        self.request.POST['format'] = '2'

    def test_scalars(self):
        widget = rag_widget(lambda r: (10, 5, 1))
        resp = widget(self.request)
        self.assertEqual(
                '{"item": [{"value": 10}, {"value": 5}, {"value": 1}]}',
                resp.content)

    def test_tuples(self):
        widget = rag_widget(lambda r: ((10, "ten"), (5, "five"),
                (1, "one")))
        resp = widget(self.request)
        self.assertEqual('{"item": [{"value": 10, "text": "ten"}, '
                '{"value": 5, "text": "five"}, {"value": 1, "text": "one"}]}',
                resp.content)


class TextDecoratorTestCase(TestCase):
    """
    Tests for the ``text`` decorator.
    """

    def setUp(self):
        super(TextDecoratorTestCase, self).setUp()
        self.settings_manager.delete('GECKOBOARD_API_KEY')
        self.request = HttpRequest()
        self.request.POST['format'] = '2'

    def test_string(self):
        widget = text_widget(lambda r: "test message")
        resp = widget(self.request)
        self.assertEqual('{"item": [{"text": "test message", "type": 0}]}',
                resp.content)

    def test_list(self):
        widget = text_widget(lambda r: ["test1", "test2"])
        resp = widget(self.request)
        self.assertEqual('{"item": [{"text": "test1", "type": 0}, '
                '{"text": "test2", "type": 0}]}', resp.content)

    def test_list_tuples(self):
        widget = text_widget(lambda r: [("test1", TEXT_NONE),
                ("test2", TEXT_INFO), ("test3", TEXT_WARN)])
        resp = widget(self.request)
        self.assertEqual('{"item": [{"text": "test1", "type": 0}, '
                '{"text": "test2", "type": 2}, '
                '{"text": "test3", "type": 1}]}', resp.content)


class PieChartDecoratorTestCase(TestCase):
    """
    Tests for the ``pie_chart`` decorator.
    """

    def setUp(self):
        super(PieChartDecoratorTestCase, self).setUp()
        self.settings_manager.delete('GECKOBOARD_API_KEY')
        self.request = HttpRequest()
        self.request.POST['format'] = '2'

    def test_scalars(self):
        widget = pie_chart(lambda r: [1, 2, 3])
        resp = widget(self.request)
        self.assertEqual(
                '{"item": [{"value": 1}, {"value": 2}, {"value": 3}]}',
                resp.content)

    def test_tuples(self):
        widget = pie_chart(lambda r: [(1, ), (2, ), (3, )])
        resp = widget(self.request)
        self.assertEqual(
                '{"item": [{"value": 1}, {"value": 2}, {"value": 3}]}',
                resp.content)

    def test_2tuples(self):
        widget = pie_chart(lambda r: [(1, "one"), (2, "two"),
                (3, "three")])
        resp = widget(self.request)
        self.assertEqual('{"item": [{"value": 1, "label": "one"}, '
                '{"value": 2, "label": "two"}, '
                '{"value": 3, "label": "three"}]}', resp.content)

    def test_3tuples(self):
        widget = pie_chart(lambda r: [(1, "one", "00112233"),
                (2, "two", "44556677"), (3, "three", "8899aabb")])
        resp = widget(self.request)
        self.assertEqual('{"item": ['
                '{"value": 1, "label": "one", "colour": "00112233"}, '
                '{"value": 2, "label": "two", "colour": "44556677"}, '
                '{"value": 3, "label": "three", "colour": "8899aabb"}]}',
                resp.content)


class LineChartDecoratorTestCase(TestCase):
    """
    Tests for the ``line_chart`` decorator.
    """

    def setUp(self):
        super(LineChartDecoratorTestCase, self).setUp()
        self.settings_manager.delete('GECKOBOARD_API_KEY')
        self.request = HttpRequest()
        self.request.POST['format'] = '2'

    def test_values(self):
        widget = line_chart(lambda r: ([1, 2, 3],))
        resp = widget(self.request)
        self.assertEqual('{"item": [1, 2, 3], "settings": {}}', resp.content)

    def test_x_axis(self):
        widget = line_chart(lambda r: ([1, 2, 3],
                ["first", "last"]))
        resp = widget(self.request)
        self.assertEqual('{"item": [1, 2, 3], '
                '"settings": {"axisx": ["first", "last"]}}', resp.content)

    def test_axes(self):
        widget = line_chart(lambda r: ([1, 2, 3],
                ["first", "last"], ["low", "high"]))
        resp = widget(self.request)
        self.assertEqual('{"item": [1, 2, 3], "settings": '
                '{"axisx": ["first", "last"], "axisy": ["low", "high"]}}',
                resp.content)

    def test_color(self):
        widget = line_chart(lambda r: ([1, 2, 3],
                ["first", "last"], ["low", "high"], "00112233"))
        resp = widget(self.request)
        self.assertEqual('{"item": [1, 2, 3], "settings": '
                '{"axisx": ["first", "last"], "axisy": ["low", "high"], '
                '"colour": "00112233"}}', resp.content)


class GeckOMeterDecoratorTestCase(TestCase):
    """
    Tests for the ``line_chart`` decorator.
    """

    def setUp(self):
        super(GeckOMeterDecoratorTestCase, self).setUp()
        self.settings_manager.delete('GECKOBOARD_API_KEY')
        self.request = HttpRequest()
        self.request.POST['format'] = '2'

    def test_scalars(self):
        widget = geck_o_meter(lambda r: (2, 1, 3))
        resp = widget(self.request)
        self.assertEqual('{"item": 2, "max": {"value": 3}, '
                '"min": {"value": 1}}', resp.content)

    def test_tuples(self):
        widget = geck_o_meter(lambda r: (2, (1, "min"), (3, "max")))
        resp = widget(self.request)
        self.assertEqual('{"item": 2, "max": {"value": 3, "text": "max"}, '
                '"min": {"value": 1, "text": "min"}}', resp.content)


class FunnelDecoratorTestCase(TestCase):
    """
    Tests for the ``funnel`` decorator
    """

    def setUp(self):
        super(FunnelDecoratorTestCase, self).setUp()
        self.settings_manager.delete('GECKOBOARD_API_KEY')
        self.request = HttpRequest()
        self.request.POST['format'] = '2'
        self.funnel_data = {
            "items":[
                (50, 'step 2'),
                (100, 'step 1'),
            ],
            "type": "reverse",
            "percentage": "hide"
        }
        self.funnel_json = {
            "items":[
                {"value": 50, "label": "step 2"},
                {"value": 100, "label": "step 1"},
            ],
            "type": "reverse",
            "percentage": "hide"
        }

    def test_funnel(self):
        widget = funnel(lambda r: self.funnel_data)
        resp = widget(self.request)
        json = simplejson.loads(resp.content)
        data = {
            'type': 'reverse',
            'percentage': 'hide',
            'item': [
                {'value': 50, 'label': 'step 2'},
                {'value': 100, 'label': 'step 1'},
            ],
        }
        self.assertEqual(json, data)

    def test_funnel_sorting(self):
        sortable_data = self.funnel_data
        sortable_data.update({
            'sort': True
        })
        widget = funnel(lambda r: sortable_data)
        resp = widget(self.request)
        json = simplejson.loads(resp.content)
        data = {
            'type': 'reverse',
            'percentage': 'hide',
            'item': [
                {'value': 100, 'label': 'step 1'},
                {'value': 50, 'label': 'step 2'},
            ],
        }
        self.assertEqual(json, data)


class BulletDecoratorTestCase(TestCase):
    """
    Tests for the ``bullet`` decorator
    """

    def setUp(self):
        super(BulletDecoratorTestCase, self).setUp()
        self.settings_manager.delete('GECKOBOARD_API_KEY')
        self.request = HttpRequest()
        self.request.POST['format'] = '2'
        self.bullet_data_minimal = {
            'label':'Some label',
            'axis_points':[0, 200, 400, 600, 800, 1000],
            'current':500,
            'comparative':600,
            'auto_scale':False,
        }

    def test_bullet_minimal(self):
        """Minimal set of parameters. Some values are computed by the decorator."""
        widget = bullet(lambda r: self.bullet_data_minimal)
        resp = widget(self.request)
        # Parse
        data = simplejson.loads(resp.content)
        # Alias for readability
        item = data['item']
        # Tests
        self.assertEqual(data['orientation'], 'horizontal')
        self.assertEqual(item['label'], "Some label")
        self.assertEqual(item['axis']['point'], [0, 200, 400, 600, 800, 1000])
        self.assertEqual(item['measure']['current']['start'], 0)
        self.assertEqual(item['measure']['current']['end'], 500)
        self.assertEqual(item['comparative']['point'], 600)
        self.assertEqual(item['range']['red']['start'], 0)
        self.assertEqual(item['range']['red']['end'], 332)
        self.assertEqual(item['range']['amber']['start'], 333)
        self.assertEqual(item['range']['amber']['end'], 666)
        self.assertEqual(item['range']['green']['start'], 667)
        self.assertEqual(item['range']['green']['end'], 1000)

    def test_auto_scale(self):
        bullet_data = self.bullet_data_minimal.copy()
        bullet_data['auto_scale'] = True
        widget = bullet(lambda r: bullet_data)

        resp = widget(self.request)
        # Parse
        data = simplejson.loads(resp.content)
        # Alias for readability
        item = data['item']
        # Tests
        self.assertEqual(data['orientation'], 'horizontal')
        self.assertEqual(item['label'], "Some label")
        self.assertEqual(item['axis']['point'], [0, 0.2, 0.4, 0.6, 0.8, 1.0])
        self.assertEqual(item['measure']['current']['start'], 0)
        self.assertEqual(item['measure']['current']['end'], 0.5)
        self.assertEqual(item['comparative']['point'], 0.6)
        self.assertEqual(item['range']['red']['start'], 0)
        self.assertEqual(item['range']['red']['end'], .33)
        self.assertEqual(item['range']['amber']['start'], .33)
        self.assertEqual(item['range']['amber']['end'], .67)
        self.assertEqual(item['range']['green']['start'], .67)
        self.assertEqual(item['range']['green']['end'], 1.0)
