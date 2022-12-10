from rest_framework import serializers
from slm.api.edit import serializers as slm_serializers


class StationSerializer(slm_serializers.StationSerializer):

    latitude = serializers.FloatField(read_only=True)
    longitude = serializers.FloatField(read_only=True)

    class Meta(slm_serializers.StationSerializer.Meta):
        fields = slm_serializers.StationSerializer.Meta.fields + [
            'latitude',
            'longitude'
        ]


class StationMapSerializer(serializers.Serializer):

    def to_representation(self, instance):
        return {
            "id": instance.pk,
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [instance.longitude / 10000, instance.latitude / 10000],
            },
            "properties": {
                "name": instance.name,
                "status": instance.status
            }
        }
