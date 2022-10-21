from slm.api.public import serializers as slm_serializers
from rest_framework import serializers


class StationListSerializer(slm_serializers.StationListSerializer):

    class Meta(slm_serializers.StationListSerializer.Meta):
        # could add additional fields here to extend the data exposed by this api
        fields = slm_serializers.StationListSerializer.Meta.fields


class StationMapSerializer(serializers.Serializer):

    def to_representation(self, instance):
        return {
            "id": instance.pk,
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [
                    instance.longitude / 10000,
                    instance.latitude / 10000
                ],
            },
            "properties": {
                "name": instance.name,
                "publish": instance.last_publish,
                "status": instance.status,
                "last_data": (
                    max(0, instance.last_data.days)
                    if instance.last_data else None
                )
            }
        }
