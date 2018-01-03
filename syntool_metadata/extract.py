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
import re
import sys
import PIL
import PIL.Image
import math
try:
    import simplejson as json
except ImportError:
    import json
import errno
import numpy
import tarfile
import logging
import tempfile
try:
    import subprocess32 as subprocess
except ImportError:
    import subprocess
import xml.etree.ElementTree

logger = logging.getLogger(__name__)

class ProductNotAvailableException(Exception):
    pass

def sign(x):
    """ """
    if x > 0.0:
        return 1.0
    else:
        return -1.0


def clamp(minimum, x, maximum):
    """ """
    return max(minimum, min(x, maximum))

def get_zxy_info(root_dir, product_id, dataset_id, min_resolution):
    """ """
    product_dir = os.path.join(root_dir, 'ingested', product_id)
    dataset_dir = os.path.join(root_dir, 'ingested', product_id, dataset_id)
    tile_dir = os.path.join(dataset_dir, 'tiles.zxy')
    metadata_file = os.path.join(dataset_dir, 'metadata.json')
    json_tile_file = os.path.join(tile_dir, 'tilemap.json')
    xml_tile_file = os.path.join(tile_dir, 'tilemap.xml')

    if not os.path.exists(product_dir):
        raise ProductNotAvailableException(product_id)

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

        west, north = map(float, point0.split(' '))
        east, south = map(float, point2.split(' '))
        width = east - west
        height = north - south
        origin = numpy.array([west, south])
        for zoom_level, resolution in resolutions.iteritems():
            if resolution <= min_resolution:
                min_resolution = resolution
                break

    elif os.path.exists(json_tile_file):
        with open(json_tile_file, 'r') as json_file:
            json_data = json.load(json_file)
        world_origin = numpy.array(json_data["tiles"]["origin"])

        min_x, min_y, max_x, max_y = json_data["bbox"]
        origin = numpy.array([min_x, min_y])
        width = max_x - min_x
        height = max_y - min_y

        for zoom_level in sorted(json_data["tilesets"], key=lambda x: int(x)):
            resolution = json_data['tilesets'][zoom_level]["units_per_pixel"]
            zoom_level = int(zoom_level)
            if resolution <= min_resolution:
                min_resolution = resolution
                break

    elif os.path.exists(xml_tile_file):
        tree = xml.etree.ElementTree.parse(xml_tile_file)
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
        tile_set_nodes = root.findall(".//TileSet")
        for tile_set_node in tile_set_nodes:
            resolution = float(tile_set_node.attrib["units-per-pixel"])
            zoom_level = int(tile_set_node.attrib["order"])
            if resolution <= min_resolution:
                min_resolution = resolution
                break
    else:
        raise Exception('Tilemap (json or xml) not found in "{}"'.format(tile_dir))

    return { 'product_id': product_id
           , 'dataset_id': dataset_id
           , 'type': 'ZXY'
           , 'resolution': resolution
           , "zoom_level": zoom_level
           , "origin": origin
           , "world_origin": world_origin
           , "tile_dir": tile_dir
           , "width": width
           , "height": height
           }, min_resolution

def get_image_info( root_dir, product_id, dataset_id, min_resolution
                  , db_storage):
    """ """
    west, north, east, south = db_storage.get_image_info(product_id, dataset_id)
    image_dir = os.path.join(root_dir, 'ingested', product_id, dataset_id)
    image_path = os.path.join(image_dir, 'imageLayer.png')
    image = PIL.Image.open(image_path, 'r')
    width, height = image.size
    resolution = (east - west) / width
    if resolution < min_resolution:
        min_resolution = resolution
    return { 'product_id': product_id
           , 'dataset_id': dataset_id
           , 'type': 'IMAGE'
           , 'resolution': resolution
           , 'width' : width
           , 'height': height
           , 'west': west
           , 'east': east
           , 'south': south
           , 'north': north
           , 'image_dir': image_dir
           }, min_resolution

def get_dataset_info(root_dir, min_resolution, product_id, dataset_id, dataset_type, db_storage):
    """ """
    if 'ZXY' == dataset_type:
        return get_zxy_info(root_dir, product_id, dataset_id, min_resolution)
    elif 'IMAGE' == dataset_type:
        return get_image_info( root_dir
                             , product_id
                             , dataset_id
                             , min_resolution
			     , db_storage
                             )
    elif 'TMS' == dataset_type:
        raise Exception('TMS not supported anymore')
    raise Exception('"{}" type not supported'.format(dataset_type))

def get_data_from_zxy(dataset, tile_size, min_resolution, x1, y1, x2, y2):
    """ """
    origin = dataset["origin"]
    world_origin = dataset["world_origin"]
    resolution = dataset["resolution"]
    zoom_level = dataset["zoom_level"]
    tile_dir = dataset["tile_dir"]
    sx1 = x1 - world_origin[0]
    sy1 = world_origin[1] - y1
    tx1 = sx1 / resolution / tile_size
    ty1 = sy1 / resolution / tile_size
    fracX1, intX1 = math.modf(tx1)
    fracY1, intY1 = math.modf(ty1)
    intX1 = int(intX1)
    intY1 = int(intY1)
    sx2 = x2 - world_origin[0]
    sy2 = world_origin[1] - y2
    tx2 = sx2 / resolution / tile_size
    ty2 = sy2 / resolution / tile_size
    fracX2, intX2 = math.modf(tx2)
    fracY2, intY2 = math.modf(ty2)
    intX2 = int(intX2)
    intY2 = int(intY2)

    dataset_width = (intX2 - intX1 + 1) * tile_size
    dataset_height = (intY1 - intY2 + 1) * tile_size
    dataset_image = None

    i = 0
    j = 0
    for intX in range(intX1, intX2 + 1):
        for intY in range(intY2, intY1 + 1):
            tile_relpath = "%i/%i/%i.png" % (zoom_level, intX, intY)
            tile_path = os.path.join(tile_dir, tile_relpath)
            if os.path.exists(tile_path):
                tile_image = PIL.Image.open(tile_path, "r")
                if dataset_image is None:
                    image_mode = tile_image.mode
                    image_palette = tile_image.palette
                    dataset_image = PIL.Image.new(image_mode, (dataset_width, dataset_height))
                dataset_image.paste(tile_image, (i * tile_size, j * tile_size))
            j = j + 1
        i = i + 1
        j = 0

    if dataset_image is None:
        # No tiles for this dataset (totally transparent tiles are not produced).
        return (None, None, None, None, None)

    new_dataset_width = int(round(dataset_width * resolution / min_resolution))
    new_dataset_height = int(round(dataset_height * resolution / min_resolution))
    dataset_image = dataset_image.resize((new_dataset_width, new_dataset_height), PIL.Image.BILINEAR)
    gx = world_origin[0] + intX1 * tile_size * resolution
    gy = world_origin[1] - intY2 * tile_size * resolution
    image_x = int(round((gx - x1) / min_resolution))
    image_y = int(round((y2 - gy) / min_resolution))
    return (dataset_image, image_x, image_y, image_mode, image_palette)

def get_data_from_image(dataset, min_resolution, x1, y1, x2, y2):
    image_path = os.path.join(dataset["image_dir"], 'imageLayer.png')
    dataset_image = PIL.Image.open(image_path, "r")
    image_mode = dataset_image.mode
    image_palette = dataset_image.palette
    dataset_width = dataset["width"]
    dataset_height = dataset["height"]
    resolution = dataset["resolution"]
    new_dataset_width = int(round(dataset_width * resolution / min_resolution))
    new_dataset_height = int(round(dataset_height * resolution / min_resolution))
    dataset_image = dataset_image.resize((new_dataset_width, new_dataset_height), PIL.Image.BILINEAR)
    gx = dataset["west"]
    gy = dataset["north"]
    image_x = int(round((gx - x1) / min_resolution))
    image_y = int(round((y2 - gy) / min_resolution))
    return (dataset_image, image_x, image_y, image_mode, image_palette)

def get_dataset_data(dataset, tile_size, min_resolution, x1, y1, x2, y2):
    """ """
    if 'ZXY' == dataset['type']:
        image, image_x, image_y, image_mode, image_palette = get_data_from_zxy(dataset, tile_size, min_resolution, x1, y1, x2, y2)
    elif 'IMAGE' == dataset['type']:
        image, image_x, image_y, image_mode, image_palette = get_data_from_image(dataset, min_resolution, x1, y1, x2, y2)
    else:
        raise Exception('"{}" type not supported'.format(dataset['type']))
    return image, image_x, image_y, image_mode, image_palette

def get(root_dir, datasets_list, x1, y1, x2, y2, min_resolution, output_format, server_host, download_dir, db_storage):
    """ """
    TILE_SIZE = 256
    IMAGE_MAX_SIZE = 8192

    if not server_host.endswith('/'):
        server_host = server_host + '/'

    if x2 < x1:
        x1, x2 = x2, x1

    if y2 < y1:
        y1, y2 = y2, y1

    p1 = numpy.array([x1, y1])
    p2 = numpy.array([x2, y2])

    dx = (p2[0] - p1[0])
    dy = (p2[1] - p1[1])
    ratio = abs(dx / dy)

    # Retrieve dataset info
    # -------------------------------------------------------------------------
    datasets = []
    for dataset in datasets_list:
        product_id, dataset_id, dataset_type = dataset.split("+")
        try:
            dataset_info, min_resolution = get_dataset_info( root_dir
                                                           , min_resolution
                                                           , product_id
                                                           , dataset_id
                                                           , dataset_type
                                                           , db_storage)
        except ProductNotAvailableException:
            _, e, _ = sys.exc_info()
            logger.debug(e)
            continue
            # Silenced because some product may be stored on a remote server
        datasets.append(dataset_info)

    # Adapt image size
    max_dimension = IMAGE_MAX_SIZE * min_resolution
    if max_dimension < abs(dx) or max_dimension < abs(dy):
        image_width = IMAGE_MAX_SIZE
        image_height = IMAGE_MAX_SIZE
        if ratio < 1.0:
            image_width = IMAGE_MAX_SIZE * ratio
            min_resolution = dy / IMAGE_MAX_SIZE
        else:
            image_height = IMAGE_MAX_SIZE / ratio
            min_resolution = dx / IMAGE_MAX_SIZE
    else:
        image_width = abs(dx) / min_resolution
        image_height = abs(dy) / min_resolution

    image_width = int(round(image_width))
    image_height = int(round(image_height))

    dx = sign(dx) * image_width * min_resolution
    dy = sign(dy) * image_height * min_resolution
    x2 = x1 + dx
    y2 = y1 + dy

    # Prepare output directory
    # -------------------------------------------------------------------------
    if not os.path.exists(download_dir):
        try:
            os.makedirs(download_dir)
        except OSError, e:
            if e.errno != errno.EEXIST:
                raise

    output_dir = tempfile.mkdtemp(dir=download_dir)
    os.chmod(output_dir, 0o755)

    # Extract data
    # -------------------------------------------------------------------------
    if 'PNG' == output_format:
        tar = tarfile.open(output_dir + ".tgz", "w:gz")
        for dataset in datasets:
            image, image_x, image_y, image_mode, image_palette = get_dataset_data( dataset
                                                                  , TILE_SIZE
                                                                  , min_resolution
                                                                  , x1, y1, x2, y2)
            if image is None:
                continue
            final_image = PIL.Image.new(image_mode, (image_width, image_height))
            final_image.paste(image, (image_x, image_y))
            if image_mode in ['P', 'L'] and image_palette is not None:
                final_image.putpalette(image_palette.palette)
            final_image_name = '{}-{}.png'.format( dataset['product_id']
                                                 , dataset['dataset_id'])
            final_image_path = os.path.join(output_dir, final_image_name)
            final_image.save(final_image_path)

            new_image_path = os.path.splitext(final_image_path)[0] + ".new.png"
            cmd = "gdal_translate -q -of PNG -a_srs %(proj)s -a_ullr %(west)f %(north)f %(east)f %(south)f \
                -gcp 0 0 %(west)f %(south)f \
                -gcp %(width)d 0 %(east)f %(south)f \
                -gcp 0 %(height)d %(west)f %(north)f \
                -gcp %(width)d %(height)d %(east)f %(north)f \
                '%(pngFile)s' '%(newPngFile)s'" % {"proj": "EPSG:3857", "west": x1, "east": x2, "north": y2, "south": y1, "width": image_width, "height": image_height, "pngFile": final_image_path, "newPngFile": new_image_path}
            subprocess.check_call(cmd, shell=True)
            os.rename(new_image_path, final_image_path)
            os.rename(new_image_path + ".aux.xml", final_image_path + ".aux.xml")

            tar.add(final_image_path, arcname=final_image_name)
            tar.add(final_image_path + ".aux.xml", arcname=final_image_name + ".aux.xml")
            os.unlink(final_image_path)
            os.unlink(final_image_path + ".aux.xml")
        os.rmdir(output_dir)
        tar.close()
        return '{}.tgz'.format(output_dir)
    elif 'NUMPY' == output_format:
        results = []
        for dataset in datasets:
            image, image_x, image_y, image_mode, image_palette = get_dataset_data( dataset
                                                                  , TILE_SIZE
                                                                  , min_resolution
								  , x1, y1, x2, y2)
            if image is None:
                continue
            final_image = PIL.Image.new(image_mode, (image_width, image_height))
            final_image.paste(image, (image_x, image_y))
            array_data = numpy.array(final_image)
            array_name = '{}-{}.npy'.format( dataset['product_id']
                                           , dataset['dataset_id'])
            array_path = os.path.join(output_dir, array_name)
            numpy.save(array_path, array_data)

            regex_str = download_dir + "/" + "(.+)"
            regex = re.compile(regex_str)
            rnd_str = regex.findall(output_dir)[0]
            results.append('{}download/{}/{}'.format(server_host, rnd_str, array_name))
	return results
