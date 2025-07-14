from slm.settings import get_setting, set_default

# your webserver should be configured to bypass Django and server
# MEDIA_ROOT / CKEDITOR_UPLOAD_PATH directly
set_default("CKEDITOR_UPLOAD_PATH", get_setting("MEDIA_ROOT") / "public/")

set_default(
    "CKEDITOR_CONFIGS",
    {
        "richtextinput": {
            "width": "100%",
        },
        "default": {
            # exportpdf is not included but still getting the api key warning in js console??
            "removePlugins": "exportpdf",
        },
    },
)

set_default("SILENCED_SYSTEM_CHECKS", []).append("ckeditor.W001")
