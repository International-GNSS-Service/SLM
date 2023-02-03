from django.forms.widgets import TextInput, TimeInput, DateInput
from django.conf import settings
from django.forms import CheckboxSelectMultiple, SplitDateTimeWidget


class AutoComplete(TextInput):

    template_name = 'slm/forms/widgets/autocomplete.html'

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
        )


class DatePicker(DateInput):
    input_type = "date"


class Time24(TimeInput):
    template_name = "slm/forms/widgets/time24.html"


class SLMCheckboxSelectMultiple(CheckboxSelectMultiple):

    template_name = 'slm/forms/widgets/checkbox_multiple.html'
    columns = 1

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context["widget"]["columns"] = self.columns
        return context

    def __init__(self, columns=columns, **kwargs):
        self.columns = columns or 1
        super().__init__(**kwargs)

    def optgroups(self, name, value, attrs=None):
        """Not a great way to do this"""
        class_list = []
        if attrs:
            class_list = attrs.get('class', '').replace(
                'is-invalid', ''
            ).replace(
                'slm-form-unpublished', ''
            ).replace(
                'form-control', ''
            ).replace(
                'slm-form-field', ''
            )
            class_list = [cls for cls in class_list.split(' ') if cls]
        if 'form-check-input' not in class_list:
            class_list.append('form-check-input')
        attrs['class'] = ' '.join(class_list)
        return super().optgroups(name, value, attrs)


class SLMDateTimeWidget(SplitDateTimeWidget):

    template_name = 'slm/forms/widgets/splitdatetime.html'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.widgets_names = ['', '']
        attrs = {
            **self.widgets[1].attrs,
            'class': ' '.join([cls for cls in
                self.widgets[1].attrs.get('class', '').split() + ['time-24hr']
                if cls
            ])
        }
        self.widgets[1] = Time24(
            attrs=attrs,
            format=None
        )

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        main_classes = context['widget']['attrs']['class']
        for cls in [
            'slm-form-unpublished',
            # 'is-invalid', invalid-feedback requires a peer to be is-invalid
            # to show
            'slm-form-field',
            'form-control'
        ]:
            main_classes = main_classes.replace(cls, '')
        context['widget']['attrs']['class'] = main_classes

        for idx, subwidget in enumerate(context['widget']['subwidgets']):
            subwidget['attrs']['class'] = ' '.join([
                cls for cls in
                subwidget['attrs'].get('class', '').split() +
                self.widgets[idx].attrs.get('class', '').split()
                if cls
            ])
        return context
