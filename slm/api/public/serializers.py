from rest_framework import serializers
from slm.models import (
    Site,
    Agency,
    Network,
    SiteFileUpload
)


class EmbeddedAgencySerializer(serializers.ModelSerializer):
    class Meta:
        model = Agency
        fields = [
            'name',
            'shortname',
            'country'
        ]

class EmbeddedNetworkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Network
        fields = [
            'name'
        ]


class StationListSerializer(serializers.ModelSerializer):

    agencies = EmbeddedAgencySerializer(many=True)
    networks = EmbeddedNetworkSerializer(many=True)
    registered = serializers.CharField(source='created')
    latitude = serializers.SerializerMethodField()
    longitude = serializers.SerializerMethodField()
    city = serializers.CharField()
    country = serializers.CharField()
    elevation = serializers.FloatField()
    antenna_type = serializers.CharField()
    radome_type = serializers.CharField()
    receiver_type = serializers.CharField()
    serial_number = serializers.CharField()
    firmware = serializers.CharField()
    frequency_standard = serializers.CharField()
    domes_number = serializers.CharField()
    satellite_system = serializers.CharField()
    data_center = serializers.CharField()
    last_rinex2 = serializers.DateTimeField()
    last_rinex3 = serializers.DateTimeField()
    last_rinex4 = serializers.DateTimeField()
    last_data_time = serializers.DateTimeField()
    last_data = serializers.SerializerMethodField()

    def get_last_data(self, obj):
        if obj.last_data:
            return max(0, obj.last_data.days)
        return None

    def get_latitude(self, obj):
        if obj.latitude is not None:
            return obj.latitude / 10000
        return obj.latitude

    def get_longitude(self, obj):
        if obj.longitude is not None:
            return obj.longitude / 10000
        return obj.longitude

    class Meta:
        model = Site
        fields = [
            'name',
            'agencies',
            'networks',
            'registered',
            'last_publish', 
            'status',
            'latitude',
            'longitude',
            'city',
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
        if 'request' in self.context:
            return self.context['request'].build_absolute_uri(obj.file.url)
        return obj.file.url

    class Meta:
        model = SiteFileUpload
        fields = [
            'id',
            'site',
            'name',
            'timestamp',
            'download',
            'mimetype',
            'description'
        ]
        read_only_fields = fields
