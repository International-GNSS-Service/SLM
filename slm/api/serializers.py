import json

from django.template.loader import get_template
from django.utils.functional import cached_property
from rest_framework import serializers
from slm.defines import SiteLogFormat, GeodesyMLVersion
from slm.models import Site


class _Heading:
    pass


_heading = _Heading()


class SiteLogSerializer(serializers.BaseSerializer):

    site = None
    epoch = None
    epoch_param = None
    published_param = True
    is_published = None
    graphic = ''

    text_tmpl = get_template('slm/sitelog/legacy.log')

    xml_tmpl = {
        #GeodesyMLVersion.v0_4: get_template('slm/sitelog/xsd/geodesyml_04.xml'),
        GeodesyMLVersion.v0_5:
            get_template('slm/sitelog/xsd/geodesyml_05.xml')
    }

    def __init__(self, *args, instance, epoch=None, published=True, **kwargs):
        self.site = instance
        self.epoch_param = epoch
        self.epoch = epoch
        self.published_param = published
        if self.epoch is None:
            self.epoch = self.site.created  # todo resolve this to the real one
        super().__init__(*args, instance=instance, **kwargs)

    def xml(self, version):
        return str(self.xml_tmpl[version].render({
            **self.context,
            'identifier': self.site.get_filename(
                log_format=SiteLogFormat.GEODESY_ML,
                epoch=self.epoch_param
            ).split('.')[0]
        }))

    @cached_property
    def json(self):
        # todo
        return json.dumps({})

    def format(self, log_format, version=None):
        if log_format == SiteLogFormat.LEGACY:
            return self.text
        elif log_format == SiteLogFormat.GEODESY_ML:
            return self.xml(version=(version or GeodesyMLVersion.latest()))
        raise NotImplementedError(
            f'Serialization for format {log_format} is not yet implemented.'
        )

    def section_name(self, name):
        if name.startswith('site'):
            return name[4:]
        return name

    @cached_property
    def context(self):
        return {
            'site': self.site,
            **{
                self.section_name(name): getattr(self.site, accessor).current(
                    epoch=self.epoch_param,
                    published=self.published_param
                )
                for name, accessor in zip(
                    Site.section_fields(),
                    Site.section_accessors()
                )
            },
            **{
                self.section_name(name): getattr(self.site, accessor).current(
                    epoch=self.epoch_param,
                    published=self.published_param
                ).filter(is_deleted=False)
                for name, accessor in zip(
                    Site.subsection_fields(),
                    Site.subsection_accessors()
                )
            },
            'graphic': getattr(
                self.site.siteantenna_set.current(
                    epoch=self.epoch_param,
                    published=self.published_param
                ).filter(is_deleted=False).last(),
                'graphic',
                ''
            ),
        }

    @cached_property
    def text(self):
        return str(self.text_tmpl.render({
            **self.context,
            'include_templates': True
        }))
