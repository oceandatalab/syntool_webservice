# -*- encoding: utf-8 -*-

"""
@author: <sylvain.herledan@oceandatalab.com>
"""

"""
Copyright (C) 2014-2018 OceanDataLab

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

from __future__ import with_statement
from webob import Request, Response, exc
from routr import route, POST, GET
from routr.exc import NoMatchFound
import syntool_metadata.db
import syntool_metadata.histogram
import syntool_metadata.extract
import ConfigParser
import datetime
try:
    import simplejson as json
except ImportError:
    import json
import sys
import os

# Load settings
# ----------------------------------------------------------------------------
settings_ini_path = os.environ.get('SYNTOOL_INI', None)
if settings_ini_path is None:
    raise Exception('Please define the SYNTOOL_INI environment variable')
if not os.path.exists(settings_ini_path):
    raise Exception('Settings file not found: {}'.format(settings_ini_path))

ini_parser = ConfigParser.ConfigParser()
ini_parser.read(settings_ini_path)

db_cfg = ini_parser._sections['database']
db_uri = 'mysql://{}:{}@{}:{}/{}'.format( db_cfg.get('user', 'syntool')
                                     , db_cfg.get('password', 'syntool')
                                     , db_cfg.get('host', 'localhost')
                                     , db_cfg.get('port', 3306)
                                     , db_cfg.get('name', 'syntool'))
storage_type = syntool_metadata.db.Storage(db_uri)

root_dir = ini_parser._sections['general']['root_dir']
download_dir = ini_parser._sections['general']['download_dir']
results_limit = int(ini_parser._sections['database'].get('results_limit',
                                                         5000))

url_prefix = os.environ.get('URL_PREFIX', '')
tile_servers = os.environ.get('SYNTOOL_TILE_SERVERS', '').split(',')
tile_servers = filter(lambda x: 0 < len(x), tile_servers)

DAY_IN_SECONDS = 24 * 60 * 60

def parse_client_product_availability(cpa):
    if cpa is None or len(cpa) == 0:
        return []

    cpa = json.loads(cpa)
    client_product_availability = []
    for i in xrange(0, len(cpa), 2):
        date_in_days = cpa[i]
        arity = cpa[i + 1]
        date = datetime.datetime.utcfromtimestamp(date_in_days * DAY_IN_SECONDS)
        client_product_availability.append((arity, date))

    return client_product_availability

# Services
# ----------------------------------------------------------------------------
def get_availability(environ, *args, **kwargs):
    """ """
    required = []
    missing = [x for x in required if x not in kwargs or 0 >= len(x)]
    if 0 < len(missing):
        msg = '{}  parameter(s) must be present in the request'
        msg = msg.format(', '.join(missing))
        return {'ok': False, 'details': msg}

    year = kwargs.get('year', None)
    if year is not None:
        if 'NaN' == year:
            year = None
        else:
            year = int(year)

    month = kwargs.get('month', None)
    if month is not None:
        if 'NaN' == month:
            month = None
        else:
            month = int(month)

    day = kwargs.get('day', None)
    if day is not None:
        if 'NaN' == day:
            day = None
        else:
            day = int(day)

    extent = kwargs.get('extent', None)
    if extent is not None and 1 > len(extent):
        extent = None

    products_filter = kwargs.get('products', None)
    if products_filter is not None:
	if 1 > len(products_filter):
            products_filter = None
        else:
            products_filter = products_filter.split(',')

    patterns = kwargs.get('patterns', None)
    if patterns is not None and 0 < len(patterns):
        patterns = dict(zip(products_filter, patterns.split(',')))
    else:
        patterns = None

    client_availability = kwargs.get('clientAvailability', None)
    if client_availability is not None and 0 < len(client_availability):
        client_availability = map(parse_client_product_availability, client_availability.split(';'))
        client_availability = dict(zip(products_filter, client_availability))
    else:
        client_availability = None

    with storage_type.get_session() as storage:
        result = storage.get_availability( year
                                         , month
                                         , day
                                         , extent
                                         , products_filter
                                         , patterns
                                         , client_availability)

    if result is None:
        result = {'years': {}, 'months': {}, 'days': {},
                  'error': 'No product available, please check that you did ' \
                           'not mispell product identifiers in the request'}

    if 'callback' in kwargs:
      return '{}({})'.format(kwargs['callback'], json.dumps(result))
    else:
      return result

def get_datasets(environ, *args, **kwargs):
    """ """
    required = [ 'minDate', 'maxDate']
    missing = [x for x in required if x not in kwargs or 0 >= len(x)]
    if 0 < len(missing):
        msg = '{}  parameter(s) must be present in the request'
        msg = msg.format(', '.join(missing))
        return {'ok': False, 'details': msg}

    extent = kwargs.get('extent', None)
    if extent is not None and 1 > len(extent):
        extent = None

    products_filter = kwargs.get('products', None)
    if products_filter is not None:
	if 1 > len(products_filter):
            products_filter = None
        else:
            products_filter = products_filter.split(',')

    patterns = kwargs.get('patterns', None)
    if patterns is not None and 0 < len(patterns):
        patterns = dict(zip(products_filter, patterns.split(',')))
    else:
        patterns = None

    minD = datetime.datetime.utcfromtimestamp(float(kwargs['minDate']))
    maxD = datetime.datetime.utcfromtimestamp(float(kwargs['maxDate']))

    with storage_type.get_session() as storage:
        datasets = storage.get_datasets( 'data/'
				       , root_dir
                                       , minD
                                       , maxD
                                       , extent
                                       , products_filter
                                       , patterns
                                       , results_limit)

    result = {'events': datasets}

    if 'callback' in kwargs:
      return '{}({})'.format(kwargs['callback'], json.dumps(result))
    else:
      return result

def search_datasets(environ, *args, **kwargs):
    """ """
    required = ['minDate', 'maxDate', 'products', 'format']
    missing = [x for x in required if x not in kwargs or 0 >= len(x)]
    if 0 < len(missing):
        msg = '{}  parameter(s) must be present in the request'
        msg = msg.format(', '.join(missing))
        return {'ok': False, 'details': msg}

    output_format = kwargs.get('format', 'url')
    if output_format not in ['url', 'path']:
        msg = 'Output format "{}" is not supported, use either "url" ou "path"'
        return {'ok': False, 'details': msg}

    if 'url' == output_format and 'SERVER_HOST' not in environ:
        msg = 'Webserver misconfigured: missing SERVER_HOST environment variable'
        return { 'ok': False, 'details': msg}

    extent = kwargs.get('extent', None)
    if extent is not None and 1 > len(extent):
        extent = None

    products_filter = kwargs.get('products', None)
    if products_filter is not None:
	if 1 > len(products_filter):
            products_filter = None
        else:
            products_filter = products_filter.split(',')

    patterns = kwargs.get('patterns', None)
    if patterns is not None and 0 < len(patterns):
        patterns = dict(zip(products_filter, patterns.split(',')))
    else:
        patterns = None

    minD = datetime.datetime.utcfromtimestamp(float(kwargs['minDate']))
    maxD = datetime.datetime.utcfromtimestamp(float(kwargs['maxDate']))

    with storage_type.get_session() as storage:
        datasets = storage.search_datasets( minD
                                          , maxD
                                          , extent
                                          , products_filter
                                          , patterns)

    result = []
    if 'url' == output_format:
        server_host = environ['SERVER_HOST']
        if not server_host.endswith('/'):
            server_host = '{}/'.format(server_host)
        for product_id, product_items in datasets.iteritems():
            product_datasets = map(lambda x: '{}data/ingested/{}/{}'.format(server_host, product_id, x), product_items)
            result.extend(product_datasets)
    elif 'path' == output_format:
        for product_id, product_items in datasets.iteritems():
            product_datasets = map(lambda x: os.path.join(product_id, x), product_items)
            result.extend(product_datasets)

    return '\n'.join(result)

def find_nearest_dataset(environ, *args, **kwargs):
    """ """
    required = [ 'date']
    missing = [x for x in required if x not in kwargs or 0 >= len(x)]
    if 0 < len(missing):
        msg = '{}  parameter(s) must be present in the request'
        msg = msg.format(', '.join(missing))
        return {'ok': False, 'details': msg}

    extent = kwargs.get('extent', None)
    if extent is not None and 1 > len(extent):
        extent = None

    products_filter = kwargs.get('products', None)
    if products_filter is not None:
	if 1 > len(products_filter):
            products_filter = None
        else:
            products_filter = products_filter.split(',')

    patterns = kwargs.get('patterns', None)
    if patterns is not None and 0 < len(patterns):
        patterns = dict(zip(products_filter, patterns.split(',')))
    else:
        patterns = None

    direction = kwargs.get('direction', None)
    if direction is not None and 1 > len(direction):
        direction = None

    d = datetime.datetime.utcfromtimestamp(float(kwargs['date']))

    with storage_type.get_session() as storage:
        ts, before, after = storage.find_nearest( direction
                                                , d
                                                , extent
                                                , products_filter
                                                , patterns
                                                , 300)

    result = { 'nearestDataDate': ts
             , 'before_delta': before
             , 'after_delta': after
    }

    if 'callback' in kwargs:
      return '{}({})'.format(kwargs['callback'], json.dumps(result))
    else:
      return result

def histogram(environ, *args, **kwargs):
    """ """
    required = [ 'productId', 'datasetId', 'x1', 'y1', 'x2', 'y2', 'zoomLevel']
    missing = [x for x in required if x not in kwargs or 0 >= len(x)]
    if 0 < len(missing):
        msg = '{}  parameter(s) must be present in the request'
        msg = msg.format(', '.join(missing))
        return {'ok': False, 'details': msg}

    dataset_id, dataset_type = kwargs['datasetId'].split('+', 1)
    result = syntool_metadata.histogram.get( root_dir
					   , kwargs['productId']
					   , dataset_id
                                           , dataset_type
					   , float(kwargs['x1'])
                                           , float(kwargs['y1'])
                                           , float(kwargs['x2'])
                                           , float(kwargs['y2'])
                                           , int(kwargs['zoomLevel']))

    if 'callback' in kwargs:
      return '{}({})'.format(kwargs['callback'], json.dumps(result))
    else:
      return result

def download_png(environ, *args, **kwargs):
    """ """
    required = ['datasets', 'x1', 'y1', 'x2', 'y2', 'resolution']
    missing = [x for x in required if x not in kwargs or 0 >= len(x)]
    if 0 < len(missing):
        msg = '{}  parameter(s) must be present in the request'
        msg = msg.format(', '.join(missing))
        return {'ok': False, 'details': msg}

    if 'SERVER_HOST' not in environ:
        msg = 'Webserver misconfigured: missing SERVER_HOST environment variable'
        return { 'ok': False, 'details': msg}

    with storage_type.get_session() as storage:
        results = syntool_metadata.extract.get( root_dir
                                              , kwargs['datasets'].split(',')
					      , float(kwargs['x1'])
                                              , float(kwargs['y1'])
                                              , float(kwargs['x2'])
                                              , float(kwargs['y2'])
                                              , float(kwargs['resolution'])
                                              , 'PNG'
                                              , environ['SERVER_HOST']
                                              , download_dir
                                              , storage)
    with open(results, 'r') as f:
        content = f.read()

    n = datetime.datetime.now()
    default_filename = 'syntool-archive-{}.tgz'.format(n.strftime('%Y%m%d_%H%M%S'))
    r = Response()
    r.body = content
    r.content_type = 'application/octet-stream'
    r.content_disposition = 'attachement; filename={}'.format(default_filename)
    r.content_description = 'File transfer'
    return r

def download_numpy(environ, *args, **kwargs):
    """ """
    required = ['datasets', 'x1', 'y1', 'x2', 'y2', 'resolution']
    missing = [x for x in required if x not in kwargs or 0 >= len(x)]
    if 0 < len(missing):
        msg = '{}  parameter(s) must be present in the request'
        msg = msg.format(', '.join(missing))
        return {'ok': False, 'details': msg}

    if 'SERVER_HOST' not in environ:
        msg = 'Webserver misconfigured: missing SERVER_HOST environment variable'
        return { 'ok': False, 'details': msg}

    with storage_type.get_session() as storage:
        results = syntool_metadata.extract.get( root_dir
                                              , kwargs['datasets'].split(',')
					      , float(kwargs['x1'])
                                              , float(kwargs['y1'])
                                              , float(kwargs['x2'])
                                              , float(kwargs['y2'])
                                              , float(kwargs['resolution'])
                                              , 'NUMPY'
                                              , environ['SERVER_HOST']
                                              , download_dir
                                              , storage)

    if 'callback' in kwargs:
      return '{}({})'.format(kwargs['callback'], json.dumps(results))
    else:
      return results

def list_products(environ, *args, **kwargs):
    """ """
    with storage_type.get_session() as storage:
        results = storage.list_products()
    return '\n'.join(['{} : {}'.format(k,v) for k,v in results.iteritems()])

# Routing
# ----------------------------------------------------------------------------
routes = route(
    route( GET
         , '{}availability.service.php'.format(url_prefix)
         , get_availability),
    route( POST
         , '{}availability.service.php'.format(url_prefix)
         , get_availability),
    route( GET
         , '{}data-noRegion.service.php'.format(url_prefix)
         , get_datasets),
    route( GET
         , '{}findnearestdata.service.php'.format(url_prefix)
         , find_nearest_dataset),
    route( GET
         , '{}histogram.service.php'.format(url_prefix)
         , histogram),
    route( GET
         , '{}downloadRaster.service.php'.format(url_prefix)
         , download_png),
    route( GET
         , '{}downloadNumpy.service.php'.format(url_prefix)
         , download_numpy),
    route( GET
         , '{}search/'.format(url_prefix)
         , search_datasets),
    route( GET
         , '{}listProducts/'.format(url_prefix)
         , list_products),
)

# WSGI application
# ----------------------------------------------------------------------------
def application(environ, start_response):
    request = Request(environ)
    try:
        trace = routes(request)
        view = trace.target
        args, kwargs = trace.args, trace.kwargs
        for param_name, param_value in request.params.iteritems():
            kwargs[param_name] = param_value

        response = view(environ, *args, **kwargs)
    except NoMatchFound:
        e = sys.exc_info()[1]
        response = e.response
    except exc.HTTPException:
        e = sys.exc_info()[1]
        response = e

    if not isinstance(response, Response):
        if isinstance(response, dict) \
        or isinstance(response, list) \
        or isinstance(response, tuple):
            response = Response(json=response)
        elif isinstance(response, basestring):
            response = Response(response)
    return response(environ, start_response)
