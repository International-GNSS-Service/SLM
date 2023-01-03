from django.http import QueryDict
from django_filters import BaseInFilter, NumberFilter


class AcceptListArguments:
    """
    Automatic conversion of lists to GET parameters in AJAX seems to add pesky
    [] to the end of list arguments - there doesn't seem to be an easy way
    to handle this in FilterSets so we strip the brackets out with this mixin.

    It seems really really stupid that this is necessary...
    """

    def __init__(self, data=None, *args, **kwargs):
        if data:
            stripped = QueryDict(mutable=True)
            for key in data.keys():
                if key.endswith('[]'):
                    stripped.setlist(key[0:-2], data.getlist(key))
                else:
                    stripped[key] = data.get(key)
            data = stripped
        super().__init__(data=data, *args, **kwargs)


class MustIncludeThese(BaseInFilter, NumberFilter):

    def __init__(self, field_name='pk', *args, **kwargs):
        super().__init__(field_name=field_name, *args, **kwargs)

    def filter(self, qs, value):
        if value:
            qs |= super().filter(qs.model.objects.all(), value)
        return qs
