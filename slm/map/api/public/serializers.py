from rest_framework import serializers

from slm.api.public import serializers as slm_serializers


class StationListSerializer(slm_serializers.StationListSerializer):
    class Meta(slm_serializers.StationListSerializer.Meta):
        # could add additional fields here to extend the data exposed by this api
        fields = slm_serializers.StationListSerializer.Meta.fields


class StationMapSerializer(serializers.Serializer):
    def to_representation(self, instance):
        return {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": (
                    [instance.llh[1], instance.llh[0]] if instance.llh else [None, None]
                ),
            },
            "properties": {
                "name": instance.name,
                "status": instance.status,
                "last_data": (
                    max(0, instance.last_data.days) if instance.last_data else None
                ),
            },
        }
