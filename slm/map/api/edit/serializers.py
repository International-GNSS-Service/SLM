from slm.api.edit import serializers as slm_serializers
from rest_framework import serializers


class StationListSerializer(slm_serializers.StationListSerializer):

    latitude = serializers.FloatField()
    longitude = serializers.FloatField()

    class Meta(slm_serializers.StationListSerializer.Meta):
        fields = slm_serializers.StationListSerializer.Meta.fields + ['latitude', 'longitude']


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
