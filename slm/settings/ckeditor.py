from slm.settings import get_setting

# your webserver should be configured to bypass Django and server
# MEDIA_ROOT / CKEDITOR_UPLOAD_PATH directly
CKEDITOR_UPLOAD_PATH = get_setting("MEDIA_ROOT") / "public/"

CKEDITOR_CONFIGS = {
    "richtextinput": {
        "width": "100%",
    },
    "default": {},
}
