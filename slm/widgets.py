from django.forms.widgets import TextInput
from django.conf import settings


class AutoComplete(TextInput):

    template_name = "slm/form_widgets/autocomplete.html"

    def __init__(self, attrs=None):
        if attrs is None:
            attrs = {}
        attrs.setdefault('data-slm-autocomplete', True)
        super().__init__(attrs=attrs)

    class Media:
        js = (
            getattr(
                settings,
                'SLM_AUTOCOMPLETE_LIB',
                'https://cdnjs.cloudflare.com/ajax/libs/'
                'jquery.devbridge-autocomplete/1.4.11/'
                'jquery.autocomplete.min.js',
            ),
            'slm/js/autocomplete.js'
        )
