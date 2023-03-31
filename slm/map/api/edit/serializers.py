from rest_framework import serializers
from slm.api.edit import serializers as slm_serializers


class StationSerializer(slm_serializers.StationSerializer):

    llh = serializers.SerializerMethodField(read_only=True)

    def get_llh(self, obj):
        return obj.llh[0], obj.llh[1], obj.llh[2]

    class Meta(slm_serializers.StationSerializer.Meta):
        fields = (
            *slm_serializers.StationSerializer.Meta.fields,
            'llh'
        )


class StationMapSerializer(serializers.Serializer):

    def to_representation(self, instance):
        return {
            "id": instance.pk,
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [instance.llh[1], instance.llh[0]],
            },
            "properties": {
                "name": instance.name,
                "status": instance.status
            }
        }
