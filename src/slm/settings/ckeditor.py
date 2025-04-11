from slm.settings import get_setting, set_default

# your webserver should be configured to bypass Django and server
# MEDIA_ROOT / CKEDITOR_UPLOAD_PATH directly
CKEDITOR_UPLOAD_PATH = get_setting("MEDIA_ROOT") / "public/"

CKEDITOR_CONFIGS = {
    "richtextinput": {
        "width": "100%",
    },
    "default": {},
}

set_default("SILENCED_SYSTEM_CHECKS", []).append("ckeditor.W001")
