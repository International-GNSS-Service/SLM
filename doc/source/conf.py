"""
Configuration file for the Sphinx documentation builder.

This file only contains a selection of the most common options. For a full
list see the documentation:
https://www.sphinx-doc.org/en/stable/usage/configuration.html
"""

from datetime import datetime
import sys
from pathlib import Path
from sphinx.ext.autodoc import between
import warnings
import os
import django

sys.path.append(str(Path(__file__).parent.parent.parent / "src"))
sys.path.append(str(Path(__file__).parent.parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tests.settings')
django.setup()

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.

# sys.path.append(str(Path(__file__).parent / 'slm' / 'examples'))
# sys.path.append(str(Path(__file__).parent / 'slm' / 'tests'))

import slm
project = slm.__title__
copyright = slm.__copyright__
author = slm.__author__
release = slm.__version__


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.todo',
    'sphinxcontrib.typer',
    'sphinx_tabs.tabs',
    'sphinxcontrib.cairosvgconverter',
    'sphinxcontrib_django',
    "sphinx.ext.viewcode",
    'sphinx.ext.intersphinx'
]

try:
    import enchant
    extensions.append('sphinxcontrib.spelling')
except ImportError as err:
    warnings.warn(f"Spell checker not available: {err}", UserWarning)

spelling_show_suggestions = True
spelling_lang = 'en_US'
spelling_word_list_filename = ['ignored_spellings.txt']
spelling_show_whole_line = False
spelling_verbose = False

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ['build', '.DS_Store']


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
#html_theme = 'sphinx_rtd_theme'
html_theme = "furo"
#html_logo = "_static/img/slm-logo.svg"

html_theme_options = {
    "source_repository": "https://github.com/International-GNSS-Service/SLM",
    "source_branch": "main",
    "source_directory": "doc/source",
    "announcement": "The Site Log Manager is maintained by the <a href='https://igs.org'>International GNSS Service (IGS)</a>.",
}
html_title = f"IGS - Site Log Manager"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = [
    '_static'
]

todo_include_todos = True

latex_engine = "xelatex"

# Include the database table names of Django models
django_show_db_tables = True                # Boolean, default: False
# Add abstract database tables names (only takes effect if django_show_db_tables is True)
django_show_db_tables_abstract = True       # Boolean, default: False


intersphinx_mapping = {
    "django": (
        "https://docs.djangoproject.com/en/stable",
        "https://docs.djangoproject.com/en/stable/_objects/",
    ),
    "click": ("https://click.palletsprojects.com/en/stable", None),
    "rich": ("https://rich.readthedocs.io/en/stable", None),
    "django-typer": ("https://django-typer.readthedocs.io/en/stable/", None),
    "django-render-static": ("https://django-render-static.readthedocs.io/en/stable/", None),
    "django-split-settings": ("https://django-split-settings.readthedocs.io/en/stable/", None),
    "django-routines": ("https://django-routines.readthedocs.io/en/stable/", None),
    "django-enum": ("https://django-enum.readthedocs.io/en/stable/", None),
    "django-filter": ("https://django-filter.readthedocs.io/en/stable/", None),
    "python": ('https://docs.python.org/3', None)
}

# extlinks = {
#     'djadmin': ('https://docs.djangoproject.com/en/stable/ref/django-admin/#%s', ''),
# }

def setup(app):
    # Register a sphinx.ext.autodoc.between listener to ignore everything
    # between lines that contain the word IGNORE
    app.connect(
        'autodoc-process-docstring',
        between('^.*[*]{79}.*$', exclude=True)
    )
    app.add_css_file('style.css')

    # todo remove when this PR is merged upstream:
    # https://github.com/sphinx-doc/sphinxcontrib-django/pull/75
    app.add_crossref_type(directivename="django-admin", rolename="django-admin")
    return app
