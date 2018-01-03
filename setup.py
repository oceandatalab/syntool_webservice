# -*- encoding: utf-8 -*-

"""
syntool_metadata: Webservices for Syntool web portals.

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
from setuptools import setup
try:
    import subprocess32 as subprocess
except ImportError:
    import subprocess

package_dir = os.path.dirname(__file__)
version_path = os.path.join(package_dir, 'VERSION.txt')

major_version = '0.1'
if os.path.exists('.git') and os.path.isdir('.git'):
    commits = subprocess.check_output([ '/usr/bin/git'
                                      , 'rev-list'
                                      , 'HEAD'
                                      , '--count']).decode('utf-8').strip()
    with open(version_path, 'w') as f:
        f.write('{}.{}'.format(major_version, commits))

with open(version_path, 'r') as f:
    version = f.read()

setup(
    zip_safe=False,
    name='syntool_metadata',
    version=version,
    author=', '.join(('Sylvain Herlédan <sylvain.herledan@oceandatalab.com>',
                      'Ziad El Khoury Hanna <ziad.khoury.hanna@oceandatalab.com>')),
    author_email='syntool@oceandatalab.com',
    url='https://git.oceandatalab.com/syntool_odl/syntool_metadata',
    packages=[ 'syntool_metadata'
             ],
    scripts=[
        'bin/syntool-add-data',
        'bin/syntool-histogram',
        'bin/syntool-extract',
    ],
    license='AGPLv3',
    description='Handle metadata retrieval and update in Syntool.',
    long_description=open('README.txt').read(),
    install_requires=[ 'sqlalchemy'
                     , 'mysql-python'
                     , 'numpy'
                     , 'Pillow'
                     , 'subprocess32'
                     , 'webob'
                     , 'routr'
    ],
    package_data={'syntool_metadata': [ 'share/cfg.ini.sample'
                                      , 'share/uwsgi.ini'
                                      , 'share/nginx.conf']
    },
)
