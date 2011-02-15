"""
Geckoboard decorators.
"""

import base64
from xml.dom.minidom import Document

try:
    from functools import wraps
except ImportError:
    from django.utils.functional import wraps  # Python 2.4 fallback

from django.conf import settings
from django.http import HttpResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.utils.datastructures import SortedDict
from django.utils.decorators import available_attrs
from django.utils import simplejson


TEXT_NONE = 0
TEXT_INFO = 2
TEXT_WARN = 1


class WidgetDecorator(object):
    """
    Geckoboard widget decorator.

    The decorated view must return a data structure suitable for
    serialization to XML or JSON for Geckoboard.  See the Geckoboard
    API docs or the source of extending classes for details.

    If the ``GECKOBOARD_API_KEY`` setting is used, the request must
    contain the correct API key, or a 403 Forbidden response is
    returned.
    """
    def __call__(self, view_func):
        def _wrapped_view(request, *args, **kwargs):
            if not _is_api_key_correct(request):
                return HttpResponseForbidden("Geckoboard API key incorrect")
            view_result = view_func(request, *args, **kwargs)
            data = self._convert_view_result(view_result)
            content = _render(request, data)
            return HttpResponse(content)
        wrapper = wraps(view_func, assigned=available_attrs(view_func))
        return csrf_exempt(wrapper(_wrapped_view))

    def _convert_view_result(self, data):
        # Extending classes do view result mangling here.
        return data

widget = WidgetDecorator()


class NumberWidgetDecorator(WidgetDecorator):
    """
    Geckoboard Number widget decorator.

    The decorated view must return a tuple `(current, [previous])`, where
    `current` is the current value and `previous` is the previous value
    of the measured quantity.
    """

    def _convert_view_result(self, result):
        if not isinstance(result, (tuple, list)):
            result = [result]
        return {'item': [{'value': v} for v in result if v is not None]}

number_widget = NumberWidgetDecorator()


class RAGWidgetDecorator(WidgetDecorator):
    """
    Geckoboard Red-Amber-Green (RAG) widget decorator.

    The decorated view must return a tuple with three tuples `(value,
    [text])`.  The `value` parameters are the numbers shown in red,
    amber and green (in that order).  The `text` parameters are optional
    and will be displayed next to the respective values in the
    dashboard.
    """

    def _convert_view_result(self, result):
        items = []
        for elem in result:
            if not isinstance(elem, (tuple, list)):
                elem = [elem]
            item = SortedDict()
            if elem[0] is None:
                item['value'] = ''
            else:
                item['value'] = elem[0]
            if len(elem) > 1:
                item['text'] = elem[1]
            items.append(item)
        return {'item': items}

rag_widget = RAGWidgetDecorator()


class TextWidgetDecorator(WidgetDecorator):
    """
    Geckoboard Text widget decorator.

    The decorated view must return a list of tuples `(message, [type])`.
    The `message` parameters are strings that will be shown in the
    widget.  The `type` parameters are optional and tell Geckoboard how
    to annotate the messages.  Use ``TEXT_INFO`` for informational
    messages, ``TEXT_WARN`` for for warnings and ``TEXT_NONE`` for plain
    text (the default).
    """

    def _convert_view_result(self, result):
        items = []
        if not isinstance(result, (tuple, list)):
            result = [result]
        for elem in result:
            if not isinstance(elem, (tuple, list)):
                elem = [elem]
            item = SortedDict()
            item['text'] = elem[0]
            if len(elem) > 1 and elem[1] is not None:
                item['type'] = elem[1]
            else:
                item['type'] = TEXT_NONE
            items.append(item)
        return {'item': items}

text_widget = TextWidgetDecorator()


class PieChartWidgetDecorator(WidgetDecorator):
    """
    Geckoboard Pie chart decorator.

    The decorated view must return a list of tuples `(value, label,
    color)`.  The color parameter is a string 'RRGGBB[TT]' representing
    red, green, blue and optionally transparency.
    """

    def _convert_view_result(self, result):
        items = []
        for elem in result:
            if not isinstance(elem, (tuple, list)):
                elem = [elem]
            item = SortedDict()
            item['value'] = elem[0]
            if len(elem) > 1:
                item['label'] = elem[1]
            if len(elem) > 2:
                item['colour'] = elem[2]
            items.append(item)
        return {'item': items}

pie_chart = PieChartWidgetDecorator()


class LineChartWidgetDecorator(WidgetDecorator):
    """
    Geckoboard Line chart decorator.

    The decorated view must return a tuple `(values, x_axis, y_axis,
    [color])`.  The `values` parameter is a list of data points.  The
    `x-axis` parameter is a label string or a list of strings, that will
    be placed on the X-axis.  The `y-axis` parameter works similarly for
    the Y-axis.  If there are more than one axis label, they are placed
    evenly along the axis.  The optional `color` parameter is a string
    ``'RRGGBB[TT]'`` representing red, green, blue and optionally
    transparency.
    """

    def _convert_view_result(self, result):
        data = SortedDict()
        data['item'] = result[0]
        data['settings'] = SortedDict()

        if len(result) > 1:
            x_axis = result[1]
            if x_axis is None:
                x_axis = ''
            if not isinstance(x_axis, (tuple, list)):
                x_axis = [x_axis]
            data['settings']['axisx'] = x_axis

        if len(result) > 2:
            y_axis = result[2]
            if y_axis is None:
                y_axis = ''
            if not isinstance(y_axis, (tuple, list)):
                y_axis = [y_axis]
            data['settings']['axisy'] = y_axis

        if len(result) > 3:
            data['settings']['colour'] = result[3]

        return data

line_chart = LineChartWidgetDecorator()


class GeckOMeterWidgetDecorator(WidgetDecorator):
    """
    Geckoboard Geck-O-Meter decorator.

    The decorated view must return a tuple `(value, min, max)`.  The
    `value` parameter represents the current value.  The `min` and `max`
    parameters represent the minimum and maximum value respectively.
    They are either a value, or a tuple `(value, text)`.  If used, the
    `text` parameter will be displayed next to the minimum or maximum
    value.
    """

    def _convert_view_result(self, result):
        value, min, max = result
        data = SortedDict()
        data['item'] = value
        data['max'] = SortedDict()
        data['min'] = SortedDict()

        if not isinstance(max, (tuple, list)):
            max = [max]
        data['max']['value'] = max[0]
        if len(max) > 1:
            data['max']['text'] = max[1]

        if not isinstance(min, (tuple, list)):
            min = [min]
        data['min']['value'] = min[0]
        if len(min) > 1:
            data['min']['text'] = min[1]

        return data

geck_o_meter = GeckOMeterWidgetDecorator()


def _is_api_key_correct(request):
    """Return whether the Geckoboard API key on the request is correct."""
    api_key = getattr(settings, 'GECKOBOARD_API_KEY', None)
    if api_key is None:
        return True
    auth = request.META.get('HTTP_AUTHORIZATION', '').split()
    if len(auth) == 2:
        if auth[0].lower() == 'basic':
            request_key = base64.b64decode(auth[1]).split(':')[0]
            return request_key == api_key
    return False


def _render(request, data):
    """Render the data to Geckoboard based on the format request parameter."""
    format = request.POST.get('format', '')
    if not format:
        format = request.GET.get('format', '')
    if format == '2':
        return _render_json(data)
    else:
        return _render_xml(data)

def _render_json(data):
    return simplejson.dumps(data)

def _render_xml(data):
    doc = Document()
    root = doc.createElement('root')
    doc.appendChild(root)
    _build_xml(doc, root, data)
    return doc.toxml()

def _build_xml(doc, parent, data):
    if isinstance(data, (tuple, list)):
        _build_list_xml(doc, parent, data)
    elif isinstance(data, dict):
        _build_dict_xml(doc, parent, data)
    else:
        _build_str_xml(doc, parent, data)

def _build_str_xml(doc, parent, data):
    parent.appendChild(doc.createTextNode(str(data)))

def _build_list_xml(doc, parent, data):
    for item in data:
        _build_xml(doc, parent, item)

def _build_dict_xml(doc, parent, data):
    for tag, item in data.items():
        if isinstance(item, (list, tuple)):
            for subitem in item:
                elem = doc.createElement(tag)
                _build_xml(doc, elem, subitem)
                parent.appendChild(elem)
        else:
            elem = doc.createElement(tag)
            _build_xml(doc, elem, item)
            parent.appendChild(elem)


class GeckoboardException(Exception):
    """
    Represents an error with the Geckoboard decorators.
    """
