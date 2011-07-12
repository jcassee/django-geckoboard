"""
Geckoboard decorators.
"""

import base64
from types import ListType, TupleType
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
        data['item'] = list(result[0])
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


class FunnelWidgetDecorator(WidgetDecorator):
    """
    Geckoboard Funnel decorator.

    The decorated view must return a dictionary with at least an `items`
    entry: `{'items': [(100, '100 %'), (50, '50 %')]}`.

    Optional keys are:

        type:       'standard' (default) or 'reverse'. Determines the
                    order of the colours.
        percentage: 'show' (default) or 'hide'. Determines whether or
                    not the percentage value is shown.
        sort:       `False` (default) or `True`. Sort the entries by
                    value or not.
    """

    def _convert_view_result(self, result):
        data = SortedDict()
        items = result.get('items', [])

        # sort the items in order if so desired
        if result.get('sort'):
            items.sort(reverse=True)

        data["item"] = [dict(zip(("value","label"), item)) for item in items]
        data["type"] = result.get('type', 'standard')
        data["percentage"] = result.get('percentage','show')
        return data

funnel = FunnelWidgetDecorator()

class BulletWidgetDecorator(WidgetDecorator):
    """
    See http://support.geckoboard.com/entries/274940-custom-chart-widget-type-definitions 
    for more information.

    The decorated method must return a dictionary containing these keys:

    Required keys:    
    label:          Main label, eg. "Revenue 2011 YTD".
    axis_points:    Points on the axis, eg. [0, 200, 400, 600, 800, 1000].
    current:        Current value range, eg. 500 or [100, 500]. A singleton 
                    500 is internally converted to [0, 500].
    comparitive:    Comparitive value, eg. 600.

    Optional keys:
    orientation:    One of 'horizontal' or 'vertical'. Defaults to horizontal.
    sublabel:       Appears below main label.
    red:            Red start and end, eg. [0,100]. Defaults are calculated 
                    from axis_points.
    amber:          Amber start and end, eg. [0,100]. Defaults are calculated 
                    from axis_points.
    green:          Green start and end, eg. [0,100]. Defaults are calculated 
                    from axis_points.
    projected:      Projected value range, eg. 900 or [100, 900]. A singleton 
                    900 is internally converted to [0, 900].
                    
    auto_scale:     If true then values will be scaled down if they  
                    do not fit into Geckoboard's UI, eg. a value of 1100 
                    is represented as 1.1. If scaling takes place the sublabel 
                    is suffixed with that information. Default is true.
    """

    def _convert_view_result(self, result):
        # Check required keys. We do not do type checking since this level of 
        # competence is assumed.
        for key in ('label', 'axis_points', 'current', 'comparitive'):
            if not result.has_key(key):
                raise RuntimeError, "Key %s is required" % key
                
        # Handle singleton current and projected
        current = result['current']
        projected = result.get('projected', None)
        if not isinstance(current, (ListType, TupleType)):
            current = [0, current]
        if (projected is not None) and not isinstance(projected, (ListType, TupleType)):
            projected = [0, projected]

        # If red, amber and green are not *all* supplied calculate defaults
        axis_points = result['axis_points']
        red = result.get('red', None)
        amber = result.get('amber', None)
        green = result.get('green', None)
        if (red is None) or (amber is None) or (green is None):
            if axis_points:
                max_point = max(axis_points)
                min_point = min(axis_points)
                third = (max_point - min_point) / 3
                red = (min_point, min_point + third - 1)
                amber = (min_point + third, max_point - third - 1)
                green = (max_point - third, max_point)
            else:
                red = amber = green = (0, 0)

        # Scan axis points for largest value and scale to avoid overflow in
        # Geckoboard's UI.
        auto_scale = result.get('auto_scale', True)
        if auto_scale and axis_points:
            scale_label_map = {1000000000:'billions', 1000000:'millions', 1000:'thousands'}
            scale = 1
            value = max(axis_points)
            for n in (1000000000, 1000000, 1000):
                if value >= n:
                    scale = n
                    break

            # Little fixedpoint helper. 
            # todo: use a fixedpoint library
            def scaler(value, scale):
                return float('%.2f' % (value*1.0 / scale))

            # Apply scale to all values
            if scale > 1:
                axis_points = [scaler(v, scale) for v in axis_points]
                current = (scaler(current[0], scale), scaler(current[1], scale))
                if projected is not None:
                    projected = (scaler(projected[0], scale), scaler(projected[1], scale))
                red = (scaler(red[0], scale), scaler(red[1], scale))
                amber = (scaler(amber[0], scale), scaler(amber[1], scale))
                green = (scaler(green[0], scale), scaler(green[1], scale))
                result['comparitive'] = scaler(result['comparitive'], scale)

                # Suffix sublabel
                sublabel = result.get('sublabel', '')
                if sublabel:
                    result['sublabel'] = '%s (%s)' % (sublabel, scale_label_map[scale])
                else:
                    result['sublabel'] = scale_label_map[scale].capitalize()

        # Assemble structure
        data = dict(
            orientation=result.get('orientation', 'horizontal'), 
            item=dict(
                label=result['label'],
                axis=dict(point=axis_points),
                range=dict(
                    red=dict(start=red[0], end=red[1]),
                    amber=dict(start=amber[0], end=amber[1]),
                    green=dict(start=green[0], end=green[1])
                ),
                measure=dict(current=dict(start=current[0], end=current[1])),
                comparitive=result['comparitive']
            )
        )
       
        # Add optional items
        if result.has_key('sublabel'):
            data['item']['sublabel'] = result['sublabel']
        if projected is not None:
            data['item']['measure']['projected'] = dict(start=projected[0], end=projected[1])

        return data

bullet = BulletWidgetDecorator()

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
