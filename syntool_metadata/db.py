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

import sqlalchemy.ext.declarative
from sqlalchemy import func,cast,desc
from sqlalchemy.types import UserDefinedType
from sqlalchemy.engine import Engine,reflection
import ConfigParser
import contextlib
import datetime
import calendar
import logging
import os

logger = logging.getLogger(__name__)

# Mappings
# ----------------------------------------------------------------------------


class Geometry(UserDefinedType):
    def get_col_spec(self):
        return "GEOMETRY"

    def bind_expression(self, bindvalue):
        return func.GeomFromText(bindvalue, type_=self)

    def column_expression(self, col):
        return func.AsText(col, type_=self)

Base = sqlalchemy.ext.declarative.declarative_base()

class Product(Base):
    """ """
    __tablename__ = 'products'
    product_id = sqlalchemy.Column(sqlalchemy.types.VARCHAR(255), primary_key=True)
    shortname = sqlalchemy.Column(sqlalchemy.types.VARCHAR(255), nullable=False)
    type = sqlalchemy.Column(sqlalchemy.types.VARCHAR(255), nullable=False)

    def __init__(self):
        """ """
        self.type = 'ZXY'

class Dataset():
    """ """
    dataset_name = sqlalchemy.Column(sqlalchemy.types.VARCHAR(255), nullable=False, primary_key=True)
    relative_path = sqlalchemy.Column(sqlalchemy.types.VARCHAR(255), nullable=False)
    begin_datetime = sqlalchemy.Column(sqlalchemy.types.DATETIME, nullable=False)
    end_datetime = sqlalchemy.Column(sqlalchemy.types.DATETIME, nullable=False)
    min_zoom_level = sqlalchemy.Column(sqlalchemy.types.INTEGER, nullable=False)
    max_zoom_level = sqlalchemy.Column(sqlalchemy.types.INTEGER, nullable=False)
    resolutions = sqlalchemy.Column(sqlalchemy.types.TEXT, nullable=False)
    bbox_text = sqlalchemy.Column(sqlalchemy.types.TEXT, nullable=False)
    bbox_geometry = sqlalchemy.Column(Geometry, nullable=True)
    shape_text = sqlalchemy.Column(sqlalchemy.types.TEXT, nullable=False)
    shape_geometry = sqlalchemy.Column(Geometry, nullable=False)


# Storage implementation
# ----------------------------------------------------------------------------
@sqlalchemy.event.listens_for(Engine, "connect")
def set_mysql_time_zone(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("SET time_zone = '+0:0'")
    cursor.close()

class Storage(object):
    """ """

    def __init__(self, db_url, *args, **kwargs):
        """ """
        super(Storage, self).__init__(*args, **kwargs)
        self.product_tables = {}
        self.__engine = sqlalchemy.create_engine( db_url, echo=False
                                                , pool_recycle=10)
        self.Base = sqlalchemy.ext.declarative.declarative_base()

    def get_product_table(self, product_id):
        fixed_product_id = product_id.replace(' ', '_')
        if fixed_product_id not in self.product_tables:
            self.product_tables[fixed_product_id] = type( 'Dataset_{}'.format(fixed_product_id)
                                                        , (self.Base, Dataset)
                                                        , {'__tablename__': 'product_{}'.format(fixed_product_id)}
                                                        )
        return self.product_tables[fixed_product_id]

    @staticmethod
    def get_product_table_name(product_id):
        return 'product_{}'.format(product_id.replace(' ', '_'))

    @contextlib.contextmanager
    def get_session(self):
        """ """
        Session = sqlalchemy.orm.sessionmaker(bind=self.__engine)
        self.__session = Session()
        try:
            yield self
            self.__session.commit()
        except:
            self.__session.rollback()
            raise
        finally:
            self.__session.close()
            logger.info('Session closed')

    def create_product( self, product_id, data_type):
        """ """
        insp = reflection.Inspector.from_engine(self.__engine)
        existing_tables = insp.get_table_names()
        if 'products' not in existing_tables:
            Product.__table__.create(self.__engine, checkfirst=True)
            self.__session.commit()
        table_name = Storage.get_product_table_name(product_id)
        if table_name not in existing_tables:
            dataset_cls = self.get_product_table(product_id)
            dataset_cls.__table__.create(self.__engine, checkfirst=True)
            self.__session.commit()

        product = self.__session.query(Product).filter_by(product_id=product_id).first()
        if product:
            created = False
        else:
            projection, product_name = product_id.split('_', 1)
            product = Product()
            product.product_id = product_id
            product.shortname = product_name.replace('_', ' ')
            product.type = data_type
            self.__session.add(product)
            created = True
        return product, created

    def create_dataset( self, product_id, name, start, stop, min_zoom, max_zoom
                   , resolutions, bbox_str, shape_str, relative_path=''):
        """ """
        dataset_cls = self.get_product_table(product_id)
        dataset = dataset_cls()
        dataset.dataset_name = name
        dataset.relative_path = relative_path
        dataset.begin_datetime = start
        dataset.end_datetime = stop
        dataset.min_zoom_level = min_zoom
        dataset.max_zoom_level = max_zoom
        dataset.resolutions = ','.join(map(str, resolutions))
        dataset.bbox_text = bbox_str
        dataset.bbox_geometry = None
        dataset.shape_text = shape_str
        dataset.shape_geometry = shape_str
        self.__session.merge(dataset)

    def get_image_info(self, product_id, dataset_id):
        """ """
        dataset_cls = self.get_product_table(product_id)
        q = self.__session.query(dataset_cls.bbox_text)
        q = q.filter(dataset_cls.dataset_name == dataset_id)
        q = q.limit(1)
        result = q.first()
        if result is None:
            return None
        if 'POINT(0 0)' == result[0]:
            if product_id.startswith('900913_') or product_id.startswith('3857_'):
                west = -20037508.34
                north = 20037508.34
                east = 20037508.34
                south = -20037508.34
            elif product_id.startswith('3413_'):
                west = -5000000
                north = 5000000
                east = 5000000
                south = -5000000
            else:
                raise Exception('Global extent unknown for {}'.format(product_id))
	else:
	    point0, _, point2, _, _ = result[0][9:-2].split(',')
            west, north = map(float, point0.split(' '))
            east, south = map(float, point2.split(' '))
        return west, north, east, south

    def get_availability(self, year, month, day, bbox_text, requested_products, patterns, client_availability):
	""" """
        insp = reflection.Inspector.from_engine(self.__engine)
        existing_tables = insp.get_table_names()
        products = [p for p in requested_products
                    if (client_availability is not None and p in client_availability)
                    or Storage.get_product_table_name(p) in existing_tables]
        if 0 >= len(products):
            return None

	# Temporal filter
	if year is None:
            date_start = None
            date_stop = None
        elif month is None:
            date_start = datetime.date(year, 1, 1)
            days_extent = 365
            if calendar.isleap(year):
                days_extent += 1
            date_stop = date_start + datetime.timedelta(days=days_extent)
        elif day is None:
            date_start = datetime.date(year, month, 1)
            _, days_extent = calendar.monthrange(year, month)
            date_stop = date_start + datetime.timedelta(days=days_extent)
        else:
            date_start = datetime.date(year, month, day)
            date_stop = date_start + datetime.timedelta(days=1)

	# Spatial filter
        bbox_polygon = None
	if bbox_text is not None:
            west, south, east, north = bbox_text.split(',')
            bbox_polygon = 'POLYGON(({} {}, {} {}, {} {}, {} {}, {} {}))'
	    bbox_polygon = bbox_polygon.format(west, north, east, north, east, south, west, south, west, north)

        result = { 'years': {}
                 , 'months': {}
                 , 'days': {}
                 }

        def update_availability(result, tkey, ttype, arity, product_index):
	    """ """
	    if tkey not in result[ttype]:
	        result[ttype][tkey] = { 'datasets': arity
				  , 'products': [product_index]}
	    else:
	        result[ttype][tkey]['datasets'] += arity
	        if product_index not in result[ttype][tkey]['products']:
		    result[ttype][tkey]['products'].append(product_index)

        all_days = []
        product_index = 0
	for product_id in products:
            product_index = product_index + 1
            pattern = None
            if patterns is not None:
                pattern = patterns.get(product_id, None)
            if client_availability is not None:
                client_product_availability = client_availability.get(product_id, [])
            else:
                client_product_availability = []
            product_availability = self.get_product_availability(product_id, date_start, date_stop, bbox_polygon, pattern)

            product_all_days = []
	    for arity, start, stop in product_availability:
                while start <= stop:
                    product_all_days.append((start.year, start.month, start.day))
		    update_availability(result, start.year, 'years', arity, product_index)
                    if start.year == year:
                        update_availability(result, start.month, 'months', arity, product_index)
                        if start.month == month:
                            update_availability(result, start.day, 'days', arity, product_index)

		    start = start + datetime.timedelta(days=1)

            for arity, start in client_product_availability:
                product_all_days.append((start.year, start.month, start.day))
                update_availability(result, start.year, 'years', arity, product_index)
                if start.year == year:
                    update_availability(result, start.month, 'months', arity, product_index)
                    if start.month == month:
                        update_availability(result, start.day, 'days', arity, product_index)
            all_days.append(set(product_all_days))

        coloc_days = set.intersection(*all_days)
        coloc_years = set([x[0] for x in coloc_days])
        coloc_months = set([x[1] for x in coloc_days if x[0] == year])

        for y in result['years']:
            if y in coloc_years:
                result['years'][y]['coloc'] = products
            else:
                result['years'][y]['coloc'] = []
        for m in result['months']:
            if m in coloc_months:
                result['months'][m]['coloc'] = products
            else:
                result['months'][m]['coloc'] = []

	return result

    @staticmethod
    def format_dataset(product_id, product_type, data_url, data_path, dataset):
	resolutions = []

        # Remove suffix for DB entries used to bypass cross-IDL issues
        dataset_name = dataset.dataset_name
        if dataset_name.endswith('_XIDLfix'):
            dataset_name = dataset_name[:-8]

        dataset_uri = '{}ingested/{}/{}{}/'.format(data_url, product_id,
                                                   dataset.relative_path,
                                                   dataset_name)

        if 'POINT(0 0)' == dataset.bbox_text:
            if product_id.startswith('900913_') or product_id.startswith('3857_'):
                west = -20037508.34
                north = 20037508.34
                east = 20037508.34
                south = -20037508.34
            elif product_id.startswith('3413_'):
                west = -5000000
                north = 5000000
                east = 5000000
                south = -5000000
            else:
                msg = 'Global extent unknown for {}'.format(product_id)
                raise Exception(msg)
	else:
	    point0, _, point2, _, _ = dataset.bbox_text[9:-2].split(',')
            west, north = map(float, point0.split(' '))
            east, south = map(float, point2.split(' '))

	if 'IMAGE' == product_type:
	    resolutions = dataset.resolutions
            uri = '{}imageLayer.png'.format(dataset_uri)
	elif product_type in ['VECTOR_FIELD', 'STREAMLINES']:
	    resolutions = dataset.resolutions
	    uri = '{}vectorFieldLayer.png'.format(dataset_uri)
	elif 'ZXY' == product_type:
	    resolutions = map(lambda x: x.split(':')[1],
                              dataset.resolutions.split(','))
            uri = '{}tiles.zxy/'.format(dataset_uri)
	elif 'TMS' == product_type:
	    resolutions = map(lambda x: x.split(':')[1],
                              dataset.resolutions.split(','))
	    uri = '{}tiles/'.format(dataset_uri)
	else:
	    uri = dataset_uri
	# DRIFT? USER?

        features = []
	features_dir = os.path.join(data_path, 'ingested', product_id,
                                    dataset.relative_path, dataset_name,
                                    'features')
        if os.path.isdir(features_dir):
            ini_parser = ConfigParser.ConfigParser()
	    for root, dirs, files in os.walk(features_dir):
                for ini_path in [os.path.join(root, fn) for fn in files if fn.lower().endswith('.ini')]:
                    ini_parser.read(ini_path)
                    feature = dict(ini_parser._sections)
                    for k in feature:
                        feature[k].pop('__name__', None)
		    if 'POLYGON' == feature['global'].get('display_type', None):
                        feature['polygon'] = feature['polygon_EPSG3857'].values()
		    features.append(feature)

        return { 'productId': product_id
               , 'datasetId': '{}-{}'.format(product_id, dataset_name)
               , 'title': dataset_name
               , 'uri': uri
               , 'start': dataset.begin_datetime.strftime('%Y-%m-%dT%H:%M:%S')
               , 'end': dataset.end_datetime.strftime('%Y-%m-%dT%H:%M:%S')
               , 'mapMinZoom': "{}".format(dataset.min_zoom_level)
               , 'mapMaxZoom': "{}".format(dataset.max_zoom_level)
               , 'mapBounds': { 'north': '{}'.format(north)
                              , 'south': '{}'.format(south)
                              , 'west': '{}'.format(west)
                              , 'east': '{}'.format(east)}
               , 'polygon': dataset.shape_text
               , 'point': { 'lon': 0.5 * (east + west)
			  , 'lat': 0.5 * (north + south)
			  }
               , 'resolutions': resolutions
               , 'features': features
               , 'type': product_type
               }

    def get_datasets( self, data_url, data_path
		    , start, stop, bbox_text, requested_products, patterns, results_limit):
        """ """
        insp = reflection.Inspector.from_engine(self.__engine)
        existing_tables = insp.get_table_names()
        products = [ p for p in requested_products if Storage.get_product_table_name(p) in existing_tables ]

        # Spatial filter
        bbox_polygon = None
        if bbox_text is not None:
            west, south, east, north = bbox_text.split(',')
            bbox_polygon = 'POLYGON(({} {}, {} {}, {} {}, {} {}, {} {}))'
            bbox_polygon = bbox_polygon.format(west, north, east, north, east, south, west, south, west, north)

        result = []
        bucket_size = results_limit
        for product_id in products:
            if 0 >= bucket_size:
                break
            product_type = self.__session.query(Product.type).filter(Product.product_id==product_id).first()[0]

            pattern = None
            if patterns is not None:
                pattern = patterns.get(product_id, None)

            dataset_cls = self.get_product_table(product_id)
            q = self.__session.query(dataset_cls)
            q = q.filter(dataset_cls.begin_datetime < stop)
            q = q.filter(dataset_cls.end_datetime > start)
            if bbox_polygon is not None:
                q = q.filter(sqlalchemy.or_(dataset_cls.shape_text=='POINT(0 0)', func.Intersects(dataset_cls.shape_geometry, func.GeomFromText(bbox_polygon))))

            if pattern is not None:
                q = q.filter(dataset_cls.dataset_name.like('%{}%'.format(pattern)))
            q = q.order_by(dataset_cls.begin_datetime)
            q = q.limit(bucket_size)
            product_datasets = map(lambda x: Storage.format_dataset(product_id, product_type, data_url, data_path, x), q.all())
            bucket_size = bucket_size - len(product_datasets)
	    result.extend(product_datasets)
        return result


    def search_datasets( self, start, stop, bbox_text, requested_products, patterns):
        """ """
        insp = reflection.Inspector.from_engine(self.__engine)
        existing_tables = insp.get_table_names()
        products = [ p for p in requested_products if Storage.get_product_table_name(p) in existing_tables ] 
        
	# Spatial filter
        bbox_polygon = None
	if bbox_text is not None:
            west, south, east, north = bbox_text.split(',')
            bbox_polygon = 'POLYGON(({} {}, {} {}, {} {}, {} {}, {} {}))'
	    bbox_polygon = bbox_polygon.format(west, north, east, north, east, south, west, south, west, north)

	results = {}

	for product_id in products:
            pattern = None
            if patterns is not None:
                pattern = patterns.get(product_id, None)
	    
            dataset_cls = self.get_product_table(product_id)
            q = self.__session.query(dataset_cls.dataset_name)
            q = q.filter(dataset_cls.begin_datetime < stop)
            q = q.filter(dataset_cls.end_datetime > start)
            if bbox_polygon is not None:
                q = q.filter(sqlalchemy.or_(dataset_cls.shape_text=='POINT(0 0)', func.Intersects(dataset_cls.shape_geometry, func.GeomFromText(bbox_polygon))))

            if pattern is not None:
                q = q.filter(dataset_cls.dataset_name.like('%{}%'.format(pattern)))
            q = q.order_by(dataset_cls.begin_datetime)
            results[product_id] = map(lambda x: x[0], q.all())
        return results

    def list_products(self, **kwargs):
        insp = reflection.Inspector.from_engine(self.__engine)
        existing_tables = insp.get_table_names()
        if 'products' not in existing_tables:
            Product.__table__.create(self.__engine, checkfirst=True)
            self.__session.commit()
        q = self.__session.query(Product.product_id, Product.shortname)
        results = { k:v for k,v in q.all() }
        return results

    def get_product_availability( self, product_id, date_start, date_stop, bbox, pattern):
        """ """
        """
        sqlQuery = "SELECT COUNT(*) AS nbDatasets, DATE_FORMAT(begin_datetime, '%Y/%m/%d') AS begin_datetime2, " \
                    "DATE_FORMAT(end_datetime, '%Y/%m/%d') AS end_datetime2 FROM `product_" + productId.replace(' ', '_') + "` " \
                    "GROUP BY begin_datetime2, end_datetime2"
        """
        insp = reflection.Inspector.from_engine(self.__engine)
        existing_tables = insp.get_table_names()
        table_name = Storage.get_product_table_name(product_id)
        if table_name not in existing_tables:
            return []
        dataset_cls = self.get_product_table(product_id)
        nb_datasets = func.count(dataset_cls.dataset_name).label('nb_datasets')
        dataset_begin = sqlalchemy.func.date(dataset_cls.begin_datetime)
        dataset_end = sqlalchemy.func.date(dataset_cls.end_datetime)
        q = self.__session.query(nb_datasets, dataset_begin, dataset_end)

        if bbox is not None:
            q = q.filter(sqlalchemy.or_(dataset_cls.shape_text=='POINT(0 0)', func.Intersects(dataset_cls.shape_geometry, func.GeomFromText(bbox))))

        if pattern is not None:
            q = q.filter(dataset_cls.dataset_name.like('%{}%'.format(pattern)))

        q = q.group_by( dataset_begin, dataset_end)
        return q.all()

    def find_nearest(self, direction, current, bbox_text, requested_products, patterns, search_step=60):
        """ """
        insp = reflection.Inspector.from_engine(self.__engine)
        existing_tables = insp.get_table_names()
        products = [ p for p in requested_products if Storage.get_product_table_name(p) in existing_tables ] 

	# Spatial filter
        bbox_polygon = None
	if bbox_text is not None:
            west, south, east, north = bbox_text.split(',')
            bbox_polygon = 'POLYGON(({} {}, {} {}, {} {}, {} {}, {} {}))'
	    bbox_polygon = bbox_polygon.format(west, north, east, north, east, south, west, south, west, north)

        after_delta = float('inf')
        before_delta = float('inf')
	for product_id in products:
            pattern = None
            if patterns is not None:
                pattern = patterns.get(product_id, None)

            dataset_cls = self.get_product_table(product_id)

            mid_ts = ((func.unix_timestamp(dataset_cls.begin_datetime) + func.unix_timestamp(dataset_cls.end_datetime)) / 2).label('mid_ts')
            current_ts = calendar.timegm(current.timetuple())

            # Look for datasets in the future
            if direction in ['nearest', 'after', None]:
                q = self.__session.query(mid_ts)
                q = q.filter(mid_ts > current_ts + search_step)
                if bbox_polygon is not None:
                    q = q.filter(sqlalchemy.or_(dataset_cls.shape_text=='POINT(0 0)', func.Intersects(dataset_cls.shape_geometry, func.GeomFromText(bbox_polygon))))
                if pattern is not None:
                    q = q.filter(dataset_cls.dataset_name.like('%{}%'.format(pattern)))
                q = q.order_by(mid_ts)
                q = q.limit(1)
		result = q.first()
                if result is not None:
                    delta = int(result[0]) - current_ts
                    if delta < after_delta:
                        after_delta = delta

	    # Look for datasets in the past
            if direction in ['nearest', 'before', None]:
                q = self.__session.query(mid_ts)
                q = q.filter(mid_ts < current_ts - search_step)
                if bbox_polygon is not None:
                    q = q.filter(sqlalchemy.or_(dataset_cls.shape_text=='POINT(0 0)', func.Intersects(dataset_cls.shape_geometry, func.GeomFromText(bbox_polygon))))
                if pattern is not None:
                    q = q.filter(dataset_cls.dataset_name.like('%{}%'.format(pattern)))
                q = q.order_by(desc(mid_ts))
                q = q.limit(1)
                result = q.first()
                if result is not None:
                    delta = current_ts - int(result[0])
                    if delta < before_delta:
                        before_delta = delta

        delta = min(after_delta, before_delta)
        if delta == float('inf'):
            new_ts = current_ts
        elif delta == after_delta:
            new_ts = current_ts + delta
        else:
            new_ts = current_ts - delta

        if before_delta == float('inf'):
            before_delta = -1
        if after_delta == float('inf'):
            after_delta = -1

	return new_ts, before_delta, after_delta
