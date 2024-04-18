from django.forms import CheckboxSelectMultiple, SplitDateTimeWidget
from django.forms.widgets import (
    DateInput,
    SelectMultiple,
    Textarea,
    TextInput,
    TimeInput,
)


class AutoComplete(TextInput):
    template_name = "slm/forms/widgets/auto_complete.html"


class EnumSelectMultiple(CheckboxSelectMultiple):
    def format_value(self, value):
        return [str(val.value) for val in value]


class AutoCompleteSelectMultiple(SelectMultiple):
    template_name = "slm/forms/widgets/auto_complete_multiple.html"

    def get_context(self, name, value, attrs):
        """
        Override our choices to just include the defaults, so only the initial
        selections are rendered into the options of select.

        There has to be a more efficient way to do this that doesnt involve
        iterating over the whole set, but would probably require more invasive
        alterations to the base class.
        """
        values = set(value or [])
        self.choices = [
            (choice, label) for choice, label in self.choices if choice in values
        ]
        return super().get_context(name, value, attrs)


class AutoCompleteEnumSelectMultiple(AutoCompleteSelectMultiple):
    def get_context(self, name, value, attrs):
        values = set(value.value for value in value or [])
        self.choices = [choice for choice in self.choices if choice[0] in values]
        return SelectMultiple.get_context(self, name, value, attrs)


class DatePicker(DateInput):
    input_type = "date"


class Time24(TimeInput):
    template_name = "slm/forms/widgets/time24.html"


class SLMCheckboxSelectMultiple(CheckboxSelectMultiple):
    template_name = "slm/forms/widgets/checkbox_multiple.html"
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
            class_list = (
                attrs.get("class", "")
                .replace("is-invalid", "")
                .replace("slm-form-unpublished", "")
                .replace("form-control", "")
                .replace("slm-form-field", "")
            )
            class_list = [cls for cls in class_list.split(" ") if cls]
        if "form-check-input" not in class_list:
            class_list.append("form-check-input")
        attrs["class"] = " ".join(class_list)
        return super().optgroups(name, value, attrs)


class SLMDateTimeWidget(SplitDateTimeWidget):
    template_name = "slm/forms/widgets/splitdatetime.html"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.widgets_names = ["", ""]
        attrs = {
            **self.widgets[1].attrs,
            "class": " ".join(
                [
                    cls
                    for cls in self.widgets[1].attrs.get("class", "").split()
                    + ["time-24hr"]
                    if cls
                ]
            ),
        }
        self.widgets[1] = Time24(attrs=attrs, format=None)

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        main_classes = context["widget"]["attrs"]["class"]
        for cls in [
            "slm-form-unpublished",
            # 'is-invalid', invalid-feedback requires a peer to be is-invalid
            # to show
            "slm-form-field",
            "form-control",
        ]:
            main_classes = main_classes.replace(cls, "")
        context["widget"]["attrs"]["class"] = main_classes

        for idx, subwidget in enumerate(context["widget"]["subwidgets"]):
            subwidget["attrs"]["class"] = " ".join(
                [
                    cls
                    for cls in subwidget["attrs"].get("class", "").split()
                    + self.widgets[idx].attrs.get("class", "").split()
                    if cls
                ]
            )
        return context


class GraphicTextarea(Textarea):
    def __init__(self, attrs=None, **kwargs):
        default_attrs = {"cols": 80, "class": "mono-spaced"}
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs, **kwargs)
