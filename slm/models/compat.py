from django.db.models import TextField
from django.db.models.query_utils import DeferredAttribute
from django.core.exceptions import ValidationError
import json


class JSONCompatDeferredAttribute(DeferredAttribute):
    """
    """
    def __set__(self, instance, value):
        try:
            instance.__dict__[self.field.name] = self.field.to_python(value)
        except (ValidationError, ValueError):
            # Django core fields allow assignment of any value, we do the same
            instance.__dict__[self.field.name] = value


class JSONField(TextField):
    """
    TODO - at some point in the future this field will be replaced with
        Django's native JSONField. Not all supported databases currently
        support native json column types in the versions installed in common
        cloud Linux builds.
    """

    descriptor_class = JSONCompatDeferredAttribute

    def to_python(self, value):
        if isinstance(value, str) and value:
            return json.loads(value)
        return value

    def get_prep_value(self, value):
        """
        Convert the database string into a dictionary.
        """
        if isinstance(value, str) and value:
            return json.loads(value)
        return value

    def get_db_prep_value(self, value, connection, prepared=False):
        """
        Convert the dictionary value into a json string.
        See get_db_prep_value_
        """
        if isinstance(value, dict):
            return json.dumps(value)
        return value

    def from_db_value(self, value, expression, connection):
        """
        Convert the database string into a dictionary.
        """
        if isinstance(value, str) and value:
            # if garbage finds its way into the database it can break access to
            #   a whole site, should expedite transition to native JSONField
            return json.loads(value)
        return value
