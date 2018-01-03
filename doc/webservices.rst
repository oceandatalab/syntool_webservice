###################
Syntool webservices
###################

availability.service.php
========================
This webservice accepts both GET and POST HTTP requests. It queries the Syntool
MySQL database to retrieve the time coverage of the registered granules that
match a set of constraints. It is used by the Syntool portal web application to
show users the years, months and days where data is available for display.

Input parameters
----------------

+--------------------+----------+---------------------------------+------------------------------------------------------------------+
| Parameter          | Required | Format                          | Example                                                          |
+--------------------+----------+---------------------------------+------------------------------------------------------------------+
| callback           | No       | string                          | processAvailability                                              |
+--------------------+----------+---------------------------------+------------------------------------------------------------------+
| year               | No       | integer [1970, now]             | 2015                                                             |
+--------------------+----------+---------------------------------+------------------------------------------------------------------+
| month              | No       | integer [1, 12]                 | 4                                                                |
+--------------------+----------+---------------------------------+------------------------------------------------------------------+
| day                | No       | integer [1, 31]                 | 14                                                               |
+--------------------+----------+---------------------------------+------------------------------------------------------------------+
| products           | No       | string,string,...               | 3857_GlobCurrent_L4_geostrophic_streamline,                      |
|                    |          |                                 | 900913_ARGO_profilers,3857_SMOS_L3_LOCEAN_SSS_raster             |
+--------------------+----------+---------------------------------+------------------------------------------------------------------+
| extent             | No       | float,float,float,float         | 18706892.551797,-21231148.973535,18706892.551797,21231148.973535 |
+--------------------+----------+---------------------------------+------------------------------------------------------------------+
| patterns           | No       | string,string,...               | ,6901687_43,                                                     |
+--------------------+----------+---------------------------------+------------------------------------------------------------------+
| clientAvailability | No       | [int,int,...];[int,int,...];... | [13276,1,13278,1,15597,1,16536,1];[16549,1]                      |
+--------------------+----------+---------------------------------+------------------------------------------------------------------+

callback
^^^^^^^^
Callback will be used as a wrapper for the result. For example if callback =
"myCallback", the webservice will return "myCallback("+str(result)+")"

year
^^^^
Ignore granules whose time coverage does not intersect the supplied year.

month
^^^^^
Ignore granules whose time coverage does not intersect the supplied month.
Requires year.

day
^^^
Ignore granules whose time coverage does not intersect the supplied day.
Requires both year and month.

products
^^^^^^^^
Only consider granules from the listed products.
The supplied parameter is a comma-separated list of product identifiers.

extent
^^^^^^
Limit availability computation to granules that intersect the supplied area.
The supplied parameter is a comma-separated list of four float values. These
values are the coordinates of the area bounding box expressed in the same
projection as the Syntool portal (EPSG:3857 for the PiMEP portal). The order of
the coordinates is West,South,East,North.

patterns
^^^^^^^^
Ignore granules whose identifier does not match the supplied pattern.
The supplied parameter is a comma-separated list of patterns. There must be as
many patterns as there are identifiers in the products parameter, listed in the
same order.
For example with an “A,B,C,D” products value, if only C and D must be filtered
using patterns, then the patterns parameter must be “,,patternC,patternD”.

clientAvailability
^^^^^^^^^^^^^^^^^^
Provide additional data coverage for granules which are not listed in the
database. This is the case for granules that only exist on the client side
(permanent or user-drawn shapes).
The supplied parameter is a semicolon-separated list of arrays. There must be a
many arrays as there are identifiers in the products parameter, listed in the
same order. Each array contains (day number, granules count) couples of values,
where day number is the number of days since 1970-01-01 and granules count is
the number of granules available for the product at this date.
For example with an “A,B,C,D” products value, if C has one client-side granule
for 2017-11-28 and 2017-11-29, then the clientAvailability parameter must be
“;;[17498,1,17499,1];”.

Output
------
The webservice returns a serialized dictionary (wrapped in a callback if
provided) which contains three mandatory keys: years, months and days, and an
additional error key in case an error occurred.

For each year, data availability is described using a dictionary which contains
three keys: coloc, datasets and products.
If a year contains at least one day where all requested products have granules
that match the search criteria, then coloc will contain the same list of
product identifiers as products. Otherwise coloc is an empty list.
The number of granules that match the search criteria is stored in the datasets
field..
The products field contains the list of products that have at least one granule
matching the search criteria. The list contains the position (0-indexed) of the
product’s identifier in the products parameter passed as input.

If the year parameter has been defined, then the months field of the result
will contain the same structure (coloc/datasets/products) for each month of the
provided year.

If both the year and month parameters have been defined, then the days field of
the result will contain the same structure (coloc/datasets/products) for each
day of the provided month.

Example
^^^^^^^
.. code-block:: json
    { "years": { 2015: {"coloc": [], "datasets": 510, "products": [0,2]}
               , 2016: {"coloc": ["PRODUCT_A", "PRODUCT_B", "PRODUCT_C"], "datasets": 73, "products": [0,1,2]}
               }
    , "months": { 1: {"coloc": [], "datasets": 12, "products": [1]}
                , 2: {"coloc": [], "datasets": 58, "products": [0,2]}
                , ...
                , 12: {"coloc": ["PRODUCT_A", "PRODUCT_B", "PRODUCT_C"], "datasets": 15, "products": [0,1,2]}
                }
    , "days": { 1: {"datasets": 3, "products": [1,2]}
              , ...
              , 31: {"datasets": 5, "products": [0,1,2]}
              }
    }


data-noRegion.service.php
=========================
This webservice accepts GET HTTP requests. It queries the Syntool MySQL
database to retrieve information about granules that match a set of
constraints. It is used by the Syntool portal web application to fill the
detailed timeline and draw data boundaries on the map.

Input parameters
----------------

+-----------+----------+-------------------------+------------------------------------------------------------------+
| Parameter | Required | Format                  | Example                                                          |
+-----------+----------+-------------------------+------------------------------------------------------------------+
| callback  | No       | string                  | processGranules                                                  |
+-----------+----------+-------------------------+------------------------------------------------------------------+
| minDate   | Yes      | timestamp               | 1512141988                                                       |
+-----------+----------+-------------------------+------------------------------------------------------------------+
| maxDate   | Yes      | timestamp               | 1512141990                                                       |
+-----------+----------+-------------------------+------------------------------------------------------------------+
| products  | No       | string,string,...       | 3857_GlobCurrent_L4_geostrophic_streamline,                      |
|           |          |                         | 900913_ARGO_profilers,3857_SMOS_L3_LOCEAN_SSS_raster             |
+-----------+----------+-------------------------+------------------------------------------------------------------+
| extent    | No       | float,float,float,float | 18706892.551797,-21231148.973535,18706892.551797,21231148.973535 |
+-----------+----------+-------------------------+------------------------------------------------------------------+
| patterns  | No       | string,string,...       | ,6901687_43,                                                     |
+-----------+----------+-------------------------+------------------------------------------------------------------+

callback
^^^^^^^^
Callback will be used as a wrapper for the result. For example if callback =
"myCallback", the webservice will return "myCallback("+str(result)+")"

minDate
^^^^^^^
Unix timestamp for the start of the time frame constraint.

maxDate
^^^^^^^
Unix timestamp for the end of the time frame constraint.

products
^^^^^^^^
Only consider granules from the listed products.
The supplied parameter is a comma-separated list of product identifiers.

extent
^^^^^^
Limit availability computation to granules that intersect the supplied area.
The supplied parameter is a comma-separated list of four float values. These
values are the coordinates of the area bounding box expressed in the same
projection as the Syntool portal (EPSG:3857 for the PiMEP portal). The order of
the coordinates is West,South,East,North.

patterns
^^^^^^^^
Ignore granules whose identifier does not match the supplied pattern.
The supplied parameter is a comma-separated list of patterns. There must be as
many patterns as there are identifiers in the products parameter, listed in the
same order.
For example with an “A,B,C,D” products value, if only C and D must be filtered
using patterns, then the patterns parameter must be “,,patternC,patternD”.

Output
------
The webservice returns a serialized dictionary (wrapped in a callback if
provided) which contains a single entry named events. This entry contains a
list of dictionaries describing the granules that match the search criteria..

The dictionaries describing granules contain a set of entries:
 * features: array of additional features to display when the granule is
             selected. These features are described using dictionaries with a
             mandatory “global” key. The “global” value is specific to Syntool
             and provides information about how the feature must be displayed.
             Extra keys may be added to provide more details about the granule
             or the feature (see ARGO example below).
 * polygon: shape of the granule as WKT polygon. Coordinates must be expressed
            in the same projection as the Syntool portal (EPSG:3857 for PiMEP).
            For granules with global coverage, POINT(0 0) is used instead.
 * mapMaxZoom: zoom level above which the data representation is not available
               anymore.
 * uri: path of the data representation files (root of the tiles pyramid,
        geojson file or full resolution image) relative to the URI of the data
        server.
 * productId: identifier of the product the granule belongs to (should be one
              of the identifiers passed in the products input parameter).
 * datasetId: identifier of the granule.
 * title: label describing the granule.
 * mapBounds: dictionary describing the bounding box of the granule, with
              coordinates expressed in the same projection as the Syntool
              portal (EPSG:3857 for PiMEP) using th e following format:
              {"west": WEST, "east": EAST, "north": NORTH, "south": SOUTH}.
 * resolutions: when appliable, array of the resolutions for which there is a
                data representation. May also contain some additional
                information for specific data representations (mask for tiled
                rasterized altimeter data, not included in PiMEP).
 * start: start of the time coverage of the granule, expressed as a string with
          the “YYYY-MM-DDThh:mm:ss” format.
 * "end": end of the time coverage of the granule, expressed as a string with
          the “YYYY-MM-DDThh:mm:ss” format.
 * type: deprecated
 * mapMinZoom: deprecated
 * point: deprecated

ARGO profiler granule example
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. code-block:: json
    { "features": [
     { "global":
       { "display_type": "PROFILE",
          "feature_type":"profile"
       }
       , "metadata":
         { "profile": "features/profile.svg",
            "cycle number": "80",
            "project": "ARGO Italy",
            "grounded": "N",
            "principal investigator": "Pierre-Marie Poulain",
            "wmo id": "6901846",
            "wmo inst. type": "Arvor, Seabird conductivity sensor",
            "data centre": "Ifremer, France",
            "positioning system": "GPS"
         }
       }
     ],
     "point": {
       "lat": 4298259.52221,
       "lon": 1925938.13915
     },
     "mapMinZoom": "0",

     "resolutions":[],
     "datasetId": "900913_ARGO_profilers-6901846_80",
     "end": "2015-05-15T00:03:40",
     "title": "6901846_80",
     "mapMaxZoom": "0",
     "uri": "data/ingested/900913_ARGO_profilers/6901846_80/",
     "start": "2015-05-15T00:03:40",
     "type": "TRAJECTORY",
     "productId": "900913_ARGO_profilers",
     "polygon":"POLYGON((1925938.13915 4298259.52221,1925938.13915 4298259.52221,1925938.13915 4298259.52221,1925938.13915 4298259.52221,1925938.13915 4298259.52221))",
     "mapBounds": {
       "west":"1925938.13915",
       "east":"1925938.13915",
       "north" :"4298259.52221",
       "south" :"4298259.52221"
     }
    }

Aquarius L3 SSS granule example
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. code-block:: josn
    { "features": [],
     "point": {"lat":0,"lon":0},
     "mapMinZoom":"0",
     "resolutions": "",
     "datasetId": "3857_AQUARIUS_L3_SSS_raster-sss20150512.v4.0cap",
     "end": "2015-05-16T00:00:00",
     "polygon": "POINT(0 0)",
     "title": "sss20150512.v4.0cap",
     "mapMaxZoom": "0",
     "uri": "data/ingested/3857_AQUARIUS_L3_SSS_raster/sss20150512.v4.0cap/imageLayer.png",
     "start":"2015-05-15T00:00:00",
     "type":"IMAGE",
     "productId":"3857_AQUARIUS_L3_SSS_raster",
     "mapBounds": {
       "west": "-20037508.34",
       "east": "20037508.34",
       "north": "20037508.34",
       "south": "-20037508.34"
     }
    }

findnearestdata.service.php
===========================
This webservice accepts GET HTTP requests. It queries the Syntool MySQL
database to find the datetime of a granule matching a set of constraints while
staying as close as possible to a reference time. It is used by the Syntool
portal web application to automatically center the timeline on a datetime where
data is available .

Input parameters
----------------

+-----------+----------+-------------------------+------------------------------------------------------------------+
| Parameter | Required | Format                  | Example                                                          |
+-----------+----------+-------------------------+------------------------------------------------------------------+
| callback  | No       | string                  | processNearest                                                   |
+-----------+----------+-------------------------+------------------------------------------------------------------+
| date      | Yes      | timestamp               | 1512141988                                                       |
+-----------+----------+-------------------------+------------------------------------------------------------------+
| products  | No       | string,string,...       | 3857_GlobCurrent_L4_geostrophic_streamline,                      |
|           |          |                         | 900913_ARGO_profilers,3857_SMOS_L3_LOCEAN_SSS_raster             |
+-----------+----------+-------------------------+------------------------------------------------------------------+
| extent    | No       | float,float,float,float | 18706892.551797,-21231148.973535,18706892.551797,21231148.973535 |
+-----------+----------+-------------------------+------------------------------------------------------------------+
| patterns  | No       | string,string,...       | ,6901687_43,                                                     |
+-----------+----------+-------------------------+------------------------------------------------------------------+
| direction | No       | string                  | nearest                                                          |
+-----------+----------+-------------------------+------------------------------------------------------------------+

callback
^^^^^^^^
Callback will be used as a wrapper for the result. For example if callback =
"myCallback", the webservice will return "myCallback("+str(result)+")"

date
^^^^
Unix timestamp of the reference datetime.

products
^^^^^^^^
Only consider granules from the listed products.
The supplied parameter is a comma-separated list of product identifiers.

extent
^^^^^^
Limit availability computation to granules that intersect the supplied area.
The supplied parameter is a comma-separated list of four float values. These
values are the coordinates of the area bounding box expressed in the same
projection as the Syntool portal (EPSG:3857 for the PiMEP portal). The order of
the coordinates is West,South,East,North.

patterns
^^^^^^^^
Ignore granules whose identifier does not match the supplied pattern.
The supplied parameter is a comma-separated list of patterns. There must be as
many patterns as there are identifiers in the products parameter, listed in the
same order.
For example with an “A,B,C,D” products value, if only C and D must be filtered
using patterns, then the patterns parameter must be “,,patternC,patternD”.

direction
^^^^^^^^^
Tell the webservice if it must look for the nearest granule in the past
(direction=before), in the future (direction=after) or in both direction
(direction=nearest, default behavior).

Output
------
The webservice returns a serialized dictionary (wrapped in a callback if
provided) which contains three entries: before_delta, after_delta and
nearestDataDate.
nearestDataDate is the timestamp of the granule matching the constraints which
is the closest to the reference time. before_delta is the absolute value of the
difference between the reference time and the closest datetime in the past.
after_delta is the absolute value of the difference between the reference time
and the closest datetime in the future.
