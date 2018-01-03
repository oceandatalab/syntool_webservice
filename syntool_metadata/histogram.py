# -*- encoding: utf-8 -*-

"""
@authors: <sylvain.gerard@oceandatalab.com>, <sylvain.herledan@oceandatalab.com>
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

import os
import sys
import math
try:
    import simplejson as json
except ImportError:
    import json
import numpy
import logging
import PIL.Image
from xml.etree import ElementTree

logger = logging.getLogger(__name__)

def get_position_from_zxy(origin, x, y):
    """ """
    sx = x - origin[0]
    sy = origin[1] - y
    return (sx, sy)

def get_histogram_value( sx, sy, dataset_dir, tiles, resolutions, zoom_level
                       , tile_size):
    """ """
    logger.debug('get value {} {} {} {}'.format(sx, sy, zoom_level, tile_size))
    if 0 > sx or 0 > sy:
        return 0

    tx = sx / resolutions[zoom_level] / tile_size
    ty = sy / resolutions[zoom_level] / tile_size

    fracX, intX = math.modf(tx)
    fracY, intY = math.modf(ty)
    tile = os.path.join( dataset_dir, 'tiles.zxy', '{}'.format(zoom_level)
                       , '{}'.format(int(intX)), '{}.png'.format(int(intY)))
    logger.debug(tile)
    if not tile in tiles:
        try:
            im = PIL.Image.open(tile, "r")
            pix = im.load()
        except:
            pix = None
        tiles[tile] = pix
    else:
        pix = tiles[tile]

    if not pix is None:
        px = int(fracX * tile_size)
        py = int(fracY * tile_size)

        try:
            return pix[px, py][0]
        except:
            return pix[px, py]
    else:
        return 0


def init(root_dir, product_id, dataset_id, dataset_type):
    """ """
    tiles = {}

    if 'ZXY' != dataset_type:
        return (None, None, None)

    tile_dir = os.path.join( root_dir, 'ingested', product_id, dataset_id
                           , 'tiles.zxy')
    metadata_file = os.path.join(root_dir, 'ingested', product_id, dataset_id, 'metadata.json')
    json_tile_file = os.path.join(tile_dir, 'tilemap.json')
    xml_tile_file = os.path.join(tile_dir, 'tilemap.xml')

    logging.debug(json_tile_file)
    logging.debug(xml_tile_file)
    if os.path.exists(metadata_file):
        with open(metadata_file, 'r') as json_file:
            json_data = json.load(json_file)
	    point0, _, point2, _, _ = json_data['bbox_str'][9:-2].split(',')
            resolutions = { int(x[0]):float(x[1]) for x in map(lambda y: y.split(':'), json_data['resolutions'])}
            epsg = json_data['syntool_id'].split('_', 1)[0]

	if epsg in ['900913', '3857']:
            world_origin = numpy.array([-20037508.34, 20037508.34])
        elif '3413' == epsg:
            world_origin = numpy.array([-5000000, 11384000])
        else:
            raise Exception('Unsupported epsg: {}'.format(epsg))

	"""
        west, north = map(float, point0.split(' '))
        east, south = map(float, point2.split(' '))
        width = east - west
        height = north - south
        origin = numpy.array([west, south])
	"""
    elif os.path.exists(json_tile_file):
        with open(json_tile_file) as json_file:
            json_data = json.load(json_file)
            world_origin = numpy.array(json_data["tiles"]["origin"])

            bbox = json_data["bbox"]
            min_x, min_y, max_x, max_y = json_data['bbox']
            origin = numpy.array([min_x, min_y])
            width = max_x - min_x
            height = max_y - min_y

            resolutions = {}
            for zoom_level in sorted(json_data["tilesets"], key=lambda x: int(x)):
                resolution = json_data['tilesets'][zoom_level]["units_per_pixel"]
                zoom_level = int(zoom_level)
                resolutions[zoom_level] = resolution
    elif os.path.exists(xml_tile_file):
        tree = ElementTree.parse(xml_tile_file)
        root = tree.getroot()
        origin_node = root.findall(".//Origin")[0]
        world_origin_x = float(origin_node.attrib['x'])
        world_origin_y = float(origin_node.attrib['y'])
        world_origin = numpy.array([world_origin_x, world_origin_y])
        bbox_node = root.findall(".//BoundingBox")[0]
        min_x = float(bbox_node.attrib['minx'])
        max_x = float(bbox_node.attrib['maxx'])
        min_y = float(bbox_node.attrib['miny'])
        max_y = float(bbox_node.attrib['maxy'])
        origin = numpy.array([min_x, min_y])
        width = max_x - min_x
        height = max_y - min_y

        resolutions = {}
        tile_set_nodes = root.findall(".//TileSet")
        for tile_set_node in tile_set_nodes:
            resolution = float(tile_set_node.attrib["units-per-pixel"])
            zoom_level = int(tile_set_node.attrib["order"])
            resolutions[zoom_level] = resolution

    return tiles, world_origin, resolutions

def get( root_dir, product_id, dataset_id, dataset_type, x1, y1, x2, y2
       , zoom_level):
    """ """
    TILE_SIZE = 256
    STEP = 256
    p1 = numpy.array([x1, y1])
    p2 = numpy.array([x2, y2])

    dx = (p2[0] - p1[0])
    dy = (p2[1] - p1[1])

    dataset_dir = os.path.join(root_dir, 'ingested', product_id, dataset_id)
    tiles, world_origin, resolutions = init( root_dir, product_id, dataset_id
                                           , dataset_type)
    param_missing = ((tiles is None) or (world_origin is None) or
                     (resolutions is None))
    if param_missing:
        return []

    logging.debug('{} {} {} {} {}'.format(x1, y1, x2, y2, zoom_level))
    logging.debug(world_origin)
    logging.debug(resolutions)
    values = []
    for i in range(STEP + 1):
        x = p1[0] + dx / STEP * i
        y = p1[1] + dy / STEP * i

        sx, sy = get_position_from_zxy(world_origin, x, y)

        value = get_histogram_value( sx, sy, dataset_dir, tiles, resolutions
                                   , zoom_level, TILE_SIZE)
        values.append(value)

    return values
