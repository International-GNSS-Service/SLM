from rest_framework import serializers
from slm.models import (
    Site,
    SiteAntenna
)
from django.utils.functional import cached_property
import json
from django.template.loader import get_template
from django.utils.translation import gettext as _

class _Heading:
    pass


_heading = _Heading()


class SiteLogSerializer(serializers.BaseSerializer):

    START = 8
    INDENT = 2
    BRANCH_INDENT = 2
    COLON_COLUMN = 33

    site = None
    epoch = None
    epoch_param = None
    published_param = True
    is_published = None
    graphic = ''

    text_tmpl = get_template('slm/sitelog/site.log')

    """
    1.x       Section
    << start >(Field Name)        COLON_COLUMN        >: (Value)
    << start >< sub_indent >(Field Name) COLON_COLUMN >: (Value)
    """
    def __init__(self, *args, instance, epoch=None, published=True, **kwargs):
        self.site = instance
        self.epoch_param = epoch
        self.published_param = published
        super().__init__(*args, instance=instance, **kwargs)

    @cached_property
    def gml(self):
        # todo
        return ''

    @cached_property
    def json(self):
        # todo
        return json.dumps({})

    @cached_property
    def text2(self):

        return str(self.text_tmpl.render({
            'site': self.site,
            'include_templates': True
        }))

    @cached_property
    def text(self):
        start = ' ' * self.START
        sitelog = f'{start}{self.site.name} Site Information Form (site log)\n'
        sitelog += f'{start}International GNSS Service\n'
        sitelog += f'{start}See Instructions at:\n'
        sitelog += f'{start}{" "*self.INDENT}https://files.igs.org/pub/station/general/sitelog_instr.txt\n'
        sitelog += '\n'

        section_numbers = list(Site.sections().keys())
        section_numbers.sort()

        graphic = ''
        for number in section_numbers:
            section = Site.sections()[number]
            if isinstance(section, dict):
                subsection_numbers = list(section.keys())
                subsection_numbers.sort()
                if len(subsection_numbers) > 0:
                    sitelog += self.section_header(
                        self.site._meta.get_field(section[subsection_numbers[0]]).related_model
                    ) + '\n'
                for sub_number in subsection_numbers:
                    sitelog += self.subsection_to_string(
                        getattr(self.site, f'{section[sub_number]}_set').current(
                            epoch=self.epoch_param,
                            published=self.published_param
                        )
                    ) + '\n'
            elif isinstance(section, str):
                sitelog += self.section_header(self.site._meta.get_field(section).related_model) + '\n'
                sitelog += self.section_to_string(getattr(self.site, f'{section}_set').current(
                    epoch=self.epoch_param,
                    published=self.published_param
                ))
            sitelog += '\n'

        if self.graphic:
            sitelog += _('Antenna Graphics with Dimensions')
            sitelog += self.graphic

        if self.epoch is None:
            self.epoch = self.site.created
        if self.is_published is None:
            self.is_published = False
        return sitelog

    def field_line(self, section, field, indent_level, prefix=''):
        start = indent_level * self.BRANCH_INDENT + self.START - len(prefix)
        start_str = start * ' '
        field_attr = getattr(section, field, _heading)
        if field_attr is _heading:
            return f'{prefix}{start_str}{field}\n'
        elif getattr(field_attr, 'no_indent', False):
            line_str = str(field_attr() if callable(field_attr) else field_attr)
        else:
            lines = str(field_attr() if callable(field_attr) else field_attr).split('\n')
            line_str = [lines[0]]
            for line in lines[1:]:
                line_str.append(f'{" " * self.COLON_COLUMN}: {line}')
            line_str = "\n".join(line_str)

        if section.legacy_name(field):
            blank = ' ' * (self.COLON_COLUMN - start - len(section.legacy_name(field)) - len(prefix))
            return f'{prefix}{start_str}{section.legacy_name(field)}{blank}: {line_str}\n'
        return line_str

    def branch_to_string(self, section, parts, indent_level, prefix=''):
        """
        parts might be a 'field' or a ('heading or field', (...parts))
        """
        branch_str = ''
        for idx, part in enumerate(parts):
            if isinstance(part, list) or isinstance(part, tuple):
                branch_str += self.field_line(
                    section=section,
                    field=part[0],
                    indent_level=indent_level,
                    prefix=prefix if idx == 0 else ''
                )
                if len(part) > 1:
                    branch_str += self.branch_to_string(
                        section=section,
                        parts=part[1],
                        indent_level=indent_level + 1
                    )
            else:
                branch_str += self.field_line(
                    section=section,
                    field=part,
                    indent_level=indent_level,
                    prefix=prefix if idx == 0 else ''
                )
        return branch_str

    def section_to_string(self, section):
        section_str = ''
        if section:
            if self.epoch is None or section.edited > self.epoch:
                self.epoch = section.edited
            if self.is_published is None:
                self.is_published = section.published
            else:
                self.is_published &= section.published
            section_str += self.branch_to_string(
                section=section,
                parts=section.structure(),
                indent_level=0
            )
        return section_str + '\n'

    def subsection_to_string(self, subsections):
        sections_str = ''
        if subsections:
            idx = 1
            last = None
            for subsection in subsections:
                if self.epoch is None or subsection.edited > self.epoch:
                    self.epoch = subsection.edited
                if self.is_published is None:
                    self.is_published = subsection.published
                else:
                    self.is_published &= subsection.published
                if subsection.is_deleted:
                    continue
                sections_str += self.branch_to_string(
                    section=subsection,
                    parts=subsection.structure(),
                    indent_level=0,
                    prefix=f'{subsection.subsection_prefix}.{idx}'
                )
                sections_str += '\n'
                idx += 1
                last = subsection
            if isinstance(last, SiteAntenna):
                self.graphic = last.graphic

        return sections_str

    def section_header(self, section):
        return f'{section.section_number()}.' \
               f'{" " * (self.START - 1 - len(str(section.section_number())))}' \
               f'{section.section_header()}\n'

    def to_representation(self, instance):
        return self
