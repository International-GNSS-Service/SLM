from rest_framework import serializers
from slm.api.public import serializers as slm_serializers


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
                    instance.longitude,
                    instance.latitude
                ],
            },
            "properties": {
                "name": instance.site.name,
                "publish": instance.begin,
                'status': instance.site.status,
                "last_data": (
                    max(0, instance.last_data.days)
                    if instance.last_data else None
                ) or 0  # todo remove this, network map can't handle nulls
            }
        }
