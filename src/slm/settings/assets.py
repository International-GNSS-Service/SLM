"""
Defines settings that control how assets are compressed and bundled using django-compressor.

https://django-compressor.readthedocs.io
"""

from slm.settings import get_setting

COMPRESS_OFFLINE = True
COMPRESS_ROOT = get_setting("STATIC_ROOT")
COMPRESS_URL = get_setting("STATIC_URL")
COMPRESS_OUTPUT_DIR = "assets"

COMPRESS_PRECOMPILERS = (
    (
        "text/javascript",
        "npx -yes esbuild@latest {infile} --bundle --minify --outfile={outfile}",
    ),
    (
        "module",
        "npx -yes esbuild@latest {infile} --bundle --minify --outfile={outfile}",
    ),
)
