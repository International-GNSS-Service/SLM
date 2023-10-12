from rest_framework import serializers
from slm.models import (
    Agency,
    Network,
    SiteFileUpload,
    Site,
    Equipment,
    Receiver,
    Antenna,
    Radome,
    ArchivedSiteLog,
    SatelliteSystem,
    SiteTideGauge
)
from slm.utils import build_absolute_url

"""
class DOMESSerializer(serializers.Serializer):

    class Meta:
        model = Site
        fields = (
            'site__id',
            'domes_number'
        )
"""

class EquipmentSerializer(serializers.ModelSerializer):
    manufacturer = serializers.CharField(
        source='manufacturer.name',
        allow_null=True
    )

    class Meta:
        model = Equipment
        fields = [
            'id',
            'model',
            'description',
            'state',
            'manufacturer'
        ]


class AntennaSerializer(EquipmentSerializer):

    class Meta(EquipmentSerializer.Meta):
        model = Antenna


class ReceiverSerializer(EquipmentSerializer):

    class Meta(EquipmentSerializer.Meta):
        model = Receiver


class RadomeSerializer(EquipmentSerializer):

    class Meta(EquipmentSerializer.Meta):
        model = Radome


class AgencySerializer(serializers.ModelSerializer):
    class Meta:
        model = Agency
        fields = [
            'id',
            'name',
            'shortname',
            'country'
        ]


class NetworkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Network
        fields = [
            'id',
            'name'
        ]


class StationNameSerializer(serializers.ModelSerializer):

    class Meta:
        model = Site
        fields = ('id', 'name',)


class SatelliteSystemSerializer(serializers.ModelSerializer):

    class Meta:
        model = SatelliteSystem
        fields = ('name',)


class SiteTideGaugeSerializer(serializers.ModelSerializer):

    name = serializers.SerializerMethodField()
    link = serializers.URLField(source='gauge.link')

    def get_name(self, obj):
        return obj.gauge.name

    class Meta:
        model = SiteTideGauge
        fields = ('name', 'link', 'distance')


class StationListSerializer(serializers.ModelSerializer):

    agencies = AgencySerializer(many=True)
    networks = NetworkSerializer(many=True)
    tide_gauges = SiteTideGaugeSerializer(
        source='tide_gauge_distances',
        many=True
    )

    satellite_system = serializers.SerializerMethodField()

    antenna_type = serializers.CharField()
    radome_type = serializers.CharField()
    antenna_serial_number = serializers.CharField()
    receiver_type = serializers.CharField()
    antcal = serializers.CharField()

    xyz = serializers.SerializerMethodField()
    llh = serializers.SerializerMethodField()
    antenna_marker_enu = serializers.SerializerMethodField()

    city = serializers.CharField()
    state = serializers.CharField()
    country = serializers.CharField()

    serial_number = serializers.CharField()
    firmware = serializers.CharField()
    domes_number = serializers.CharField()
    frequency_standard = serializers.CharField()

    data_center = serializers.CharField()

    last_rinex2 = serializers.DateField()
    last_rinex3 = serializers.DateField()
    last_rinex4 = serializers.DateField()
    last_data_time = serializers.DateField()
    last_data = serializers.SerializerMethodField()

    def get_xyz(self, obj):
        return obj.xyz[0], obj.xyz[1], obj.xyz[2]

    def get_llh(self, obj):
        return obj.llh[0], obj.llh[1], obj.llh[2]

    def get_antenna_marker_enu(self, obj):
        return (
            obj.antenna_marker_enu[0],
            obj.antenna_marker_enu[1],
            obj.antenna_marker_enu[2]
        )

    def get_satellite_system(self, obj):
        """
        This should produce no additional queries b/c of the prefetching.
        """
        for receiver in obj.sitereceiver_set.all():
            return [
                sys.name
                for sys in receiver.satellite_system.all()
            ]
        return []

    def get_last_data(self, obj):
        if obj.last_data:
            return max(0, obj.last_data.days)
        return None

    class Meta:
        model = Site
        fields = [
            'name',
            'agencies',
            'networks',
            'join_date',
            'last_publish',
            'xyz',
            'llh',
            'city',
            'state',
            'country',
            'antenna_type',
            'antenna_serial_number',
            'antenna_marker_enu',
            'radome_type',
            'antcal',
            'receiver_type',
            'serial_number',
            'firmware',
            'frequency_standard',
            'domes_number',
            'satellite_system',
            'tide_gauges',
            'data_center',
            'last_rinex2',
            'last_rinex3',
            'last_rinex4',
            'last_data_time',
            'last_data',
        ]


class SiteFileUploadSerializer(serializers.ModelSerializer):

    site = serializers.CharField(source='site.name', allow_null=True)
    download = serializers.SerializerMethodField()

    def get_download(self, obj):
        return build_absolute_url(
            obj.link,
            request=self.context.get('request', None)
        )

    class Meta:
        model = SiteFileUpload
        fields = [
            'id',
            'site',
            'name',
            'timestamp',
            'created',
            'download',
            'mimetype',
            'description',
            'direction'
        ]
        read_only_fields = fields


class ArchiveSerializer(serializers.ModelSerializer):

    site = serializers.CharField(source='site.name', allow_null=True)

    class Meta:
        model = ArchivedSiteLog
        fields = [
            'id',
            'site',
            'name',
            'timestamp',
            'mimetype',
            'log_format',
            'size'
        ]
        read_only_fields = fields
