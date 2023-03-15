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
    SatelliteSystem
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


class StationListSerializer(serializers.ModelSerializer):

    agencies = AgencySerializer(many=True)
    networks = NetworkSerializer(many=True)
    satellite_system = serializers.SerializerMethodField()

    antenna_type = serializers.CharField()
    radome_type = serializers.CharField()
    receiver_type = serializers.CharField()

    latitude = serializers.FloatField()
    longitude = serializers.FloatField()
    elevation = serializers.FloatField()

    city = serializers.CharField()
    state = serializers.CharField()
    country = serializers.CharField()

    serial_number = serializers.CharField()
    firmware = serializers.CharField()
    domes_number = serializers.CharField()
    frequency_standard = serializers.CharField()

    data_center = serializers.CharField()

    last_rinex2 = serializers.DateTimeField()
    last_rinex3 = serializers.DateTimeField()
    last_rinex4 = serializers.DateTimeField()
    last_data_time = serializers.DateTimeField()
    last_data = serializers.SerializerMethodField()

    def get_satellite_system(self, obj):
        """
        This should produce no additional queries b/c of the prefetching.
        """
        for receiver in reversed(obj.sitereceiver_set.all()):
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
            'latitude',
            'longitude',
            'city',
            'state',
            'country',
            'elevation',
            'antenna_type',
            'radome_type',
            'receiver_type',
            'serial_number',
            'firmware',
            'frequency_standard',
            'domes_number',
            'satellite_system',
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
