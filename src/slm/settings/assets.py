"""
Defines settings that control how assets are compressed and bundled using django-compressor.

https://django-compressor.readthedocs.io
"""

from slm.settings import get_setting, set_default

set_default("COMPRESS_OFFLINE", True)
set_default("COMPRESS_ROOT", get_setting("STATIC_ROOT"))
set_default("COMPRESS_URL", get_setting("STATIC_URL"))
set_default("COMPRESS_OUTPUT_DIR", "assets")

set_default(
    "COMPRESS_PRECOMPILERS",
    (
        (
            "text/javascript",
            "npx -yes esbuild@0.25.12 {infile} --bundle --minify --outfile={outfile}",
        ),
        (
            "module",
            "npx -yes esbuild@0.25.12 {infile} --bundle --minify --outfile={outfile}",
        ),
    ),
)
