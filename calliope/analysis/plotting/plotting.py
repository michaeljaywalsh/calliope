"""
Copyright (C) 2013-2018 Calliope contributors listed in AUTHORS.
Licensed under the Apache 2.0 License (see LICENSE file).

plotting.py
~~~~~~~~~~~

Functionality to plot model data.

"""

import os
import re

import plotly.offline as pltly
import jinja2

from calliope.exceptions import warn
from calliope.analysis.plotting.capacity import plot_capacity
from calliope.analysis.plotting.timeseries import plot_timeseries
from calliope.analysis.plotting.transmission import plot_transmission
from calliope.analysis.plotting.util import type_of_script


def plot_summary(model, out_file=None, mapbox_access_token=None):
    """
    Plot a summary containing timeseries, installed capacities, and
    transmission plots. Returns a HTML string if ``out_file`` not
    given, else None.

    Parameters
    ----------
    out_file : str, optional
        Path to output file to save HTML to.
    mapbox_access_token : str, optional
        (passed to plot_transmission) If given and a valid Mapbox API
        key, a Mapbox map is drawn for lat-lon coordinates, else
        (by default), a more simple built-in map.

    """
    subset = {'costs': ['monetary']}

    timeseries = _plot(*plot_timeseries(model, subset=subset), html_only=True)
    capacity = _plot(*plot_capacity(model, subset=subset), html_only=True)
    transmission = _plot(*plot_transmission(
        model, html_only=True, mapbox_access_token=mapbox_access_token
    ), html_only=True)

    template_path = os.path.join(
        os.path.dirname(__file__), '..', '..', 'config', 'plots_template.html'
    )
    with open(template_path, 'r') as f:
        html_template = jinja2.Template(f.read())

    html = html_template.render(
        model_name=model._model_data.attrs['model.name'],
        calliope_version=model._model_data.attrs['calliope_version'],
        solution_time=(model._model_data.attrs['solution_time'] / 60),
        time_finished=model._model_data.attrs['time_finished'],
        top=timeseries,
        bottom_left=capacity,
        bottom_right=transmission,
    )

    # Strip plotly-inserted style="..." attributes
    html = re.sub(r'style=".+?"', '', html)

    if out_file:
        with open(out_file, 'w') as f:
            f.write(html)
    else:
        return html


def _plot(data, layout, html_only=False, to_file=False, **kwargs):
    plotly_kwargs = dict(
        show_link=False,
        config={
            'displaylogo': False,
            'modeBarButtonsToRemove': ['sendDataToCloud'],
        }
    )

    if type_of_script() == 'jupyter':
        plotter = pltly.iplot
        plotly_filename_key = 'filename'
        pltly.init_notebook_mode(connected=True)
    else:
        plotter = pltly.plot
        plotly_filename_key = 'image_filename'
        plotly_kwargs['auto_open'] = kwargs.get('auto_open', True)

    if to_file:
        filename, image_type = to_file.rsplit('.', 1)
        # Plotly can only save certain file types
        if image_type not in ['png', 'jpeg', 'svg', 'webp']:
            raise TypeError(
                'Unable to save plot as `{}`, choose from '
                '[`png`, `jpeg`, `svg`, `webp`]'.format(image_type)
            )
        if 'updatemenus' in layout:
            raise ValueError('Unable to save multiple arrays to SVG, pick one array only')
        else:
            plotly_kwargs.update(image=image_type)
            plotly_kwargs[plotly_filename_key] = filename

    if data:
        if html_only:
            return pltly.plot(
                {'data': data, 'layout': layout},
                include_plotlyjs=False, output_type='div',
                **plotly_kwargs
            )
        else:
            plotter({'data': data, 'layout': layout}, **plotly_kwargs)
    else:
        raise ValueError('No data to plot.')


class ModelPlotMethods:
    def __init__(self, model):
        self._model = model

    _docstring_additions = """
    html_only : bool, optional; default = False
        Returns a html string for embedding the plot in a webpage
    to_file : False or str, optional; default = False
        Will save plot to file, with name and extension given in the string.
        E.g. `save='plot.svg'` to save to svg, `save='plot.png' for static image
        Allowed extensions are: ['png', 'jpeg', 'svg', 'webp'].

    """

    def check_optimality(self):
        termination = self._model._model_data.attrs.get(
            'termination_condition', 'did_not_yet_run')
        if termination not in ['optimal', 'did_not_yet_run']:
            warn('Model termination condition was not optimal. Plotting may fail!')

    def timeseries(self, **kwargs):
        self.check_optimality()
        data, layout = plot_timeseries(self._model, **kwargs)
        return _plot(data, layout, **kwargs)

    timeseries.__doc__ = plot_timeseries.__doc__.rstrip() + _docstring_additions

    def capacity(self, **kwargs):
        self.check_optimality()
        data, layout = plot_capacity(self._model, **kwargs)
        return _plot(data, layout, **kwargs)

    capacity.__doc__ = plot_capacity.__doc__.rstrip() + _docstring_additions

    def transmission(self, **kwargs):
        self.check_optimality()
        data, layout = plot_transmission(self._model, **kwargs)
        return _plot(data, layout, **kwargs)

    transmission.__doc__ = plot_transmission.__doc__.rstrip() + _docstring_additions

    def summary(self, **kwargs):
        self.check_optimality()
        return plot_summary(self._model, **kwargs)

    summary.__doc__ = plot_summary.__doc__
