from __future__ import absolute_import
from __future__ import unicode_literals

import os.path
import shutil

TOP = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def copy_example(service_name, destination):
    template_dir = os.path.join(TOP, 'tests/examples', service_name)
    destination = destination.join(service_name, abs=1)
    shutil.copytree(template_dir, destination.strpath)
    return destination
