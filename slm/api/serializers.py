import json

from django.template.loader import get_template
from django.utils.functional import cached_property
from lxml import etree
from rest_framework import serializers

from slm.defines import GeodesyMLVersion, SiteLogFormat, SiteLogStatus
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
    graphic = ""

    text_tmpl = get_template("slm/sitelog/legacy.log")
    text_9char_tmpl = get_template("slm/sitelog/ascii_9char.log")

    xml_parser = etree.XMLParser(remove_blank_text=True)

    def __init__(self, *args, instance, epoch=None, published=True, **kwargs):
        self.site = instance
        self.epoch_param = epoch
        self.epoch = epoch
        self.published_param = (bool(epoch) or published) or None
        self.is_published = self.published_param or (
            self.site.status not in SiteLogStatus.unpublished_states()
        )
        if self.epoch is None:
            self.epoch = (
                self.site.last_publish
                if self.published_param
                else self.site.last_update or self.site.created
            )
        super().__init__(*args, instance=instance, **kwargs)

    def xml(self, version):
        return etree.tostring(
            etree.fromstring(
                version.template.render(
                    {
                        **self.context,
                        "identifier": self.site.get_filename(
                            log_format=SiteLogFormat.GEODESY_ML, epoch=self.epoch_param
                        ).split(".")[0],
                        "files": self.site.sitefileuploads.public().order_by(
                            "timestamp"
                        ),
                    }
                ).encode(),
                parser=self.xml_parser,
            ),
            pretty_print=True,
        ).decode()

    @cached_property
    def json(self):
        # todo
        return json.dumps({})

    def format(self, log_format, version=None):
        if log_format == SiteLogFormat.LEGACY:
            return self.text
        elif log_format == SiteLogFormat.ASCII_9CHAR:
            return self.text_9char
        elif log_format == SiteLogFormat.GEODESY_ML:
            return self.xml(version=(version or GeodesyMLVersion.latest()))
        raise NotImplementedError(
            f"Serialization for format {log_format} is not yet implemented."
        )

    def section_name(self, name):
        if name.startswith("site"):
            return name[4:]
        return name

    @cached_property
    def context(self):
        def sort(subsections):
            if subsections:
                return subsections.sort()
            return subsections

        # todo put this logic on the site model?
        graphic = ""
        if self.published_param:
            ant = self.site.siteantenna_set.published(epoch=self.epoch_param).last()
            graphic = ant.graphic if ant else ""
        else:
            antennas = self.site.siteantenna_set.head(
                epoch=self.epoch_param, include_deleted=False
            ).sort(reverse=True)
            if antennas:
                graphic = antennas[0].graphic

        return {
            "site": self.site,
            **{
                self.section_name(section.field): (
                    getattr(self.site, section.accessor).published(
                        epoch=self.epoch_param
                    )
                    if self.published_param
                    else sort(
                        getattr(self.site, section.accessor).head(
                            epoch=self.epoch_param, include_deleted=False
                        )
                    )
                )
                for section in Site.sections()
            },
            "graphic": graphic,
        }

    @cached_property
    def text(self):
        return self.text_tmpl.render({**self.context, "include_templates": True})

    @cached_property
    def text_9char(self):
        return self.text_9char_tmpl.render({**self.context, "include_templates": True})
