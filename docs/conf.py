from __future__ import unicode_literals

import os
import sys

sys.path.append(os.path.abspath('..'))

extensions = []

templates_path = ['_templates']

source_suffix = '.rst'

master_doc = 'index'

project = 'django-cabinet'
copyright = '2017 Feinheit AG'

version = __import__('cabinet').__version__
release = version

pygments_style = 'sphinx'

html_theme = 'alabaster'

html_static_path = ['_static']

htmlhelp_basename = 'djangocabinetdoc'

latex_documents = [(
    'index',
    'djangocabinet.tex',
    'django-cabinet Documentation',
    'Feinheit AG',
    'manual',
)]

man_pages = [(
    'index',
    'djangocabinet',
    'django-cabinet Documentation',
    ['Feinheit AG'],
    1,
)]

texinfo_documents = [(
    'index',
    'djangocabinet',
    'django-cabinet Documentation',
    'Feinheit AG',
    'djangocabinet',
    'Authentication utilities for Django',
    'Miscellaneous',
)]
