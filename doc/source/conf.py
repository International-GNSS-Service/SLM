"""
Configuration file for the Sphinx documentation builder.

This file only contains a selection of the most common options. For a full
list see the documentation:
https://www.sphinx-doc.org/en/master/usage/configuration.html
"""

from datetime import datetime
import sys
from pathlib import Path
from sphinx.ext.autodoc import between
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'slm.tests.settings')
django.setup()

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.

# sys.path.append(str(Path(__file__).parent / 'slm' / 'examples'))
# sys.path.append(str(Path(__file__).parent / 'slm' / 'tests'))

sys.path.append(str(Path(__file__).parent.parent.parent))
import slm

# -- Project information -----------------------------------------------------

project = 'IGS Site Log Manager'
copyright = f'2022-{datetime.now().year}, NASA/Jet Propulsion Laboratory'
author = ", ".join(['Ashley Santiago', 'Rachel Pham', 'Brian Kohan'])

# The full version, including alpha/beta/rc tags
release = slm.__version__


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx_rtd_theme',
    'sphinx.ext.autodoc',
    'sphinx.ext.todo',
    'sphinxcontrib.typer',
    'sphinx_tabs.tabs'
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'sphinx_rtd_theme'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = [
    '_static'
]

todo_include_todos = True


def setup(app):
    # Register a sphinx.ext.autodoc.between listener to ignore everything
    # between lines that contain the word IGNORE
    app.connect(
        'autodoc-process-docstring',
        between('^.*[*]{79}.*$', exclude=True)
    )
    app.add_css_file('style.css')
    return app
