import typing as t
from enum import Enum

from click import Context, Parameter, ParamType
from click.shell_completion import CompletionItem
from django.core.management import CommandError
from django.utils.translation import gettext as _


class EnumParser(ParamType):
    enum: t.Type[Enum]
    field: str = "value"

    @property
    def __name__(self):
        return self.enum.__name__

    def __init__(self, enum: t.Type[Enum], field: str = field):
        self.enum = enum
        self.field = field

    def convert(
        self, value: t.Any, param: t.Optional[Parameter], ctx: t.Optional[Context]
    ):
        """
        Convert a given value to the Enumeration type.
        """
        # we have to return the value because typer also registers a converter for
        # any enum type parameter that expects a value to be passed in. This is a
        # design flaw in typer - should use an isinstance test before bailing
        if isinstance(value, self.enum):
            return value.value
        try:
            for en in self.enum:
                if str(getattr(en, self.field)) == value:
                    return en.value
            return self.enum(value).value
        except ValueError as err:
            raise CommandError(
                _("{value} is not a valid {param}").format(
                    value=value, param=param.name
                )
            ) from err

    def shell_complete(
        self, ctx: "Context", param: "Parameter", incomplete: str
    ) -> t.List["CompletionItem"]:
        completions = []
        for en in self.enum:
            str_val = str(getattr(en, self.field))
            if str_val.startswith(incomplete):
                completions.append(CompletionItem(str_val))
        return completions
