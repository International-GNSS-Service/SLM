from django.contrib.auth import get_user_model
from django.utils.timezone import now
from rest_framework import serializers
from slm import signals as slm_signals
from slm.models import (
    Agency,
    Alert,
    LogEntry,
    Network,
    ReviewRequest,
    Site,
    SiteFileUpload,
    UserProfile,
)
from django.core.exceptions import PermissionDenied
from django.utils.translation import gettext as _
from django.db.models import Q
from slm.utils import build_absolute_url
from django.urls import reverse


class EmbeddedAgencySerializer(serializers.ModelSerializer):

    class Meta:
        model = Agency
        fields = [
            'id',
            'name',
            'country',
            'active'
        ]
        extra_kwargs = {
            'id': {'read_only': False},
            'name': {'read_only': True},
            'country': {'read_only': True},
            'active': {'read_only': True}
        }


class EmbeddedNetworkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Network
        fields = [
            'id',
            'name'
        ]


class EmbeddedUserSerializer(serializers.ModelSerializer):

    agencies = EmbeddedAgencySerializer(many=True, required=False)

    class Meta:
        model = get_user_model()
        fields = [
            'id',
            'email',
            'first_name',
            'last_name',
            'agencies'
        ]


class StationSerializer(serializers.ModelSerializer):

    owner = EmbeddedUserSerializer(many=False, read_only=True)
    last_user = EmbeddedUserSerializer(many=False, read_only=True)
    agencies = EmbeddedAgencySerializer(many=True, required=False)
    networks = EmbeddedNetworkSerializer(many=True, read_only=True)
    max_alert = serializers.IntegerField(read_only=True)

    can_publish = serializers.SerializerMethodField(read_only=True)

    publish = serializers.BooleanField(write_only=True, required=False)

    def get_can_publish(self, obj):
        if 'request' in self.context:
            return obj.can_publish(self.context['request'].user)
        return None

    def update(self, instance, validated_data):
        if validated_data.get('publish', False):
            if not instance.can_publish(self.context['request'].user):
                raise PermissionDenied(
                    _('You do not have permission to publish the site log.')
                )
            instance.publish(request=self.context['request'])
            # this might have been cached by an annotation - clear it in case
            # because publish may invalidate it
            if hasattr(instance, '_review_pending'):
                del instance._review_pending
        return instance

    def create(self, validated_data):
        # strip out anything but name or agencies
        validated_data.pop('publish', None)
        validated_data['name'] = validated_data['name'].upper()
        agencies = Agency.objects.filter(
            pk__in=[acy['id'] for acy in validated_data.pop('agencies', [])]
        )
        if not self.context['request'].user.can_propose_site(
            agencies=agencies
        ):
            raise PermissionDenied(
                'You do not have permission to propose a new site with the '
                'given agencies.'
            )

        new_site = super().create(validated_data)
        new_site.agencies.set(agencies)

        slm_signals.site_proposed.send(
            sender=self,
            site=new_site,
            user=self.context['request'].user,
            timestamp=new_site.created,
            request=self.context['request'],
            agencies=new_site.agencies.all()
        )
        return new_site

    class Meta:
        model = Site
        fields = [
            'id',
            'name',
            'agencies',
            'networks',
            'created',
            'status',
            'owner',
            'num_flags',
            'last_publish',
            'last_update',
            'last_user',
            'can_publish',
            'publish',
            'review_pending',
            'max_alert'
        ]
        extra_kwargs = {
            field: {'read_only': True} for field in fields if field not in {
                'name', 'publish', 'owner', 'last_user',
                'agencies', 'networks', 'can_publish'
            }
        }


class ReviewRequestSerializer(serializers.ModelSerializer):

    site_name = serializers.CharField(source='site.name', required=True)
    site = StationSerializer(many=False, read_only=True)
    requester = EmbeddedUserSerializer(many=False, read_only=True)
    review_pending = None

    def create(self, validated_data):
        validated_data['requester'] = getattr(
            self.context['request'],
            'user',
            None
        )
        validated_data['site'] = Site.objects.get(
            name__iexact=validated_data['site']['name']
        )
        request = ReviewRequest.objects.update_or_create(
            site=validated_data['site'],
            defaults={
                'requester': validated_data['requester'],
                'timestamp': now()
            }
        )[0]
        validated_data['site'].update_status(save=True)
        request.refresh_from_db()
        self.review_pending = validated_data['site'].review_pending
        return request

    class Meta:
        model = ReviewRequest
        fields = ['site_name', 'site', 'requester', 'timestamp']


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

    target = serializers.SerializerMethodField()

    def get_target(self, obj):
        if obj.target:
            if isinstance(obj.target, Site):
                return {
                    'type': 'Site',
                    'id': obj.target.id,
                    'name': obj.target.name
                }
            elif isinstance(obj.target, Agency):
                return {
                    'type': 'Agency',
                    'id': obj.target.id,
                    'name': obj.target.name
                }
            elif isinstance(obj.target, get_user_model()):
                return {
                    'type': 'User',
                    'id': obj.target.id,
                    'name': obj.target.name,
                    'email': obj.target.email
                }
        return None

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
            'target'
        ]
        read_only_fields = fields


class UserProfileSerializer(serializers.ModelSerializer):

    class Meta:
        model = UserProfile
        fields = [
            'phone1',
            'phone2',
            'address1',
            'address2',
            'address3',
            'city',
            'state_province',
            'country',
            'postal_code',
            'registration_agency'
        ]


class UserSerializer(UserProfileSerializer):

    agencies = EmbeddedAgencySerializer(many=True, read_only=True)

    profile = UserProfileSerializer(many=False)

    def update(self, instance, validated_data):

        if not hasattr(instance, 'profile') or instance.profile is None:
            UserProfile.objects.create(user=instance)

        if 'profile' in validated_data:
            self.fields.get('profile').update(
                instance=instance.profile,
                validated_data=validated_data.pop('profile')
            )
        return super().update(instance=instance, validated_data=validated_data)

    class Meta:
        model = get_user_model()
        fields = [
            'id',
            'email',
            'first_name',
            'last_name',
            'date_joined',
            'silence_emails',
            'html_emails',
            'agencies',
            'profile'
        ]
        read_only_fields = ['id', 'agencies', 'date_joined']


class SiteFileUploadSerializer(serializers.ModelSerializer):

    site = serializers.CharField(source='site.name', allow_null=True)
    site_status = serializers.IntegerField(
        source='site.status',
        read_only=True
    )
    site_flags = serializers.IntegerField(
        source='site.num_flags',
        read_only=True
    )
    user = EmbeddedUserSerializer(many=False)

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
            'site_status',
            'site_flags',
            'name',
            'user',
            'status',
            'timestamp',
            'file_type',
            'log_format',
            'mimetype',
            'description',
            'direction',
            'download'
        ]
        read_only_fields = [
            field for field in fields
            if field not in {'status', 'name', 'description', 'direction'}
        ]
