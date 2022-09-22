from rest_framework import serializers
from django.contrib.auth import get_user_model
from slm.models import (
    Site,
    UserProfile,
    Agency,
    LogEntry,
    Alert
)


class EmbeddedAgencySerializer(serializers.ModelSerializer):
    class Meta:
        model = Agency
        fields = [
            'id',
            'name',
            'country',
            'active'
        ]


class EmbeddedUserSerializer(serializers.ModelSerializer):

    agency = EmbeddedAgencySerializer(many=False, required=False)

    class Meta:
        model = get_user_model()
        fields = [
            'id',
            'email',
            'first_name',
            'last_name',
            'agency'
        ]


class StationListSerializer(serializers.ModelSerializer):

    owner = EmbeddedUserSerializer(many=False)
    last_user = EmbeddedUserSerializer(many=False)
    agencies = EmbeddedAgencySerializer(many=True)

    class Meta:
        model = Site
        fields = [
            'id',
            'name',
            'agencies',
            'created',
            'status',
            'owner',
            'num_flags',
            'last_publish',
            'last_update',
            'last_user'
        ]


class LogEntrySerializer(serializers.ModelSerializer):

    site = serializers.CharField(source='site.name')
    user = EmbeddedUserSerializer(many=False)

    class Meta:
        model = LogEntry
        fields = [
            'type',
            'site',
            'timestamp',
            'user',
            'target',
            'epoch',
            'ip'
        ]
        read_only_fields = fields


class AlertSerializer(serializers.ModelSerializer):

    site = serializers.CharField(source='site.name', allow_null=True)
    user = EmbeddedUserSerializer(many=False)
    agency = EmbeddedAgencySerializer(many=False)

    class Meta:
        model = Alert
        fields = [
            'id',
            'level',
            'header',
            'detail',
            'timestamp',
            'sticky',
            'expires',
            'site',
            'user',
            'agency'
        ]
        read_only_fields = fields


class UserSerializer(serializers.ModelSerializer):

    agency = serializers.CharField(source='agency.name', allow_null=True, required=False)

    # profile fields
    phone1 = serializers.CharField(source='profile.phone1', allow_null=True)
    phone2 = serializers.CharField(source='profile.phone2', allow_null=True)
    address1 = serializers.CharField(source='profile.address1', allow_null=True)
    address2 = serializers.CharField(source='profile.address2', allow_null=True)
    address3 = serializers.CharField(source='profile.address3', allow_null=True)
    city = serializers.CharField(source='profile.city', allow_null=True)
    state_province = serializers.CharField(source='profile.state_province', allow_null=True)
    country = serializers.CharField(source='profile.country', allow_null=True)
    postal_code = serializers.CharField(source='profile.postal_code', allow_null=True)
    registration_agency = serializers.CharField(source='profile.registration_agency', allow_null=True)
    html_emails = serializers.BooleanField(source='profile.html_emails', allow_null=True)

    def update(self, instance, validated_data):

        if not hasattr(instance, 'profile') or instance.profile is None:
            UserProfile.objects.create(**{'user': instance, **validated_data.get('profile')})
        else:
            for field, value in validated_data.get('profile', {}).items():
                setattr(instance.profile, field, value)
            instance.profile.save()

        for field, val in validated_data.items():
            if field != 'profile':
                setattr(instance, field, val)

        instance.save()
        return instance

    class Meta:
        model = get_user_model()
        fields = [
            'id',
            'email',
            'first_name',
            'last_name',
            'date_joined',
            'agency',
            'phone1',
            'phone2',
            'address1',
            'address2',
            'address3',
            'city',
            'state_province',
            'country',
            'postal_code',
            'registration_agency',
            'html_emails'
        ]
        read_only_fields = ('id', 'agency', 'date_joined')

