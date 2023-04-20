from django.apps import AppConfig, apps
from django.dispatch import Signal
from django.db.models.signals import (
    post_init,
    post_save,
    pre_delete,
    post_delete,
    post_migrate
)
from django.dispatch import receiver
from django.core.checks import Warning, register, Error, Tags
from django.utils.translation import gettext as _
from django.utils.module_loading import import_string
from django.conf import settings
from slm.defines import GeodesyMLVersion
from slm.signals import signal_name
from pprint import pformat
from tqdm import tqdm
from slm.utils import clear_caches


@register('slm', Tags.security)
def check_permission_groups_setting(**kwargs):
    error_id = 'slm.E002'
    header = _('settings.SLM_DEFAULT_PERMISSION_GROUPS is invalid')
    group_setting = getattr(settings, 'SLM_DEFAULT_PERMISSION_GROUPS', {})
    errors = []
    if group_setting:
        for group_name, permissions in group_setting.items():
            if not isinstance(group_name, str):
                errors.append(Error(
                    header,
                    hint=_('{} is not a group name string.').format(
                        str(group_name)
                    ),
                    id=error_id
                ))
                continue

            try:
                for perm in permissions:
                    if not isinstance(perm, str):
                        errors.append(Error(
                            header,
                            hint=_(
                                'SLM_DEFAULT_PERMISSION_GROUPS[{}][{}] is not '
                                'a permission codename string.'
                                'instead of {}.'
                            ).format(group_name, str(perm)),
                            id=error_id
                        ))

            except TypeError:
                errors.append(Error(
                    header,
                    hint=_(
                        '{} must be an iterable list of permission code names '
                        'instead of {}.'
                    ).format(
                        group_name,
                        type(permissions)
                    ),
                    id=error_id
                ))
    return errors


@register('slm', Tags.security)
def check_permissions_setting(**kwargs):
    warning_id = 'slm.W001'
    permissions = getattr(settings, 'SLM_PERMISSIONS', None)
    if permissions:
        try:
            from django.utils.module_loading import import_string
            import_string(permissions)
        except ImportError:
            return [
                Warning(
                    _(
                        f'Was unable to load SLM_PERMISSIONS callable: '
                        f'{permissions}'
                    ),
                    hint=_(
                        'Set SLM_PERMISSIONS to the import string for a '
                        'callable that returns a queryset of valid system'
                        'permissions.'
                    ),
                    id=warning_id
                )
            ]
    return []


@register('slm', Tags.signals)
def check_automated_alerts(**kwargs):
    error_id = 'slm.E001'

    def alert_conf_error(hint):
        return Error(
            _('settings.SLM_AUTOMATED_ALERTS is incorrect.'),
            hint,
            error_id
        )

    alerts = getattr(settings, 'SLM_AUTOMATED_ALERTS', {})
    if not isinstance(alerts, dict):
        return [
            alert_conf_error(_(
                'SLM_AUTOMATED_ALERTS is a {} but it must be a dictionary'
                'keyed on Alert model labels, the values are dictionaries '
                'containing the signals configured to issue the alert and/or'
                'rescind the alert and any default Alert model parameter '
                'overrides.')
                .format(type(alerts))
            )
        ]
    errors = []
    for alert, config in alerts.items():
        try:
            AlertModel = apps.get_model(*alert.split('.', 1))
        except LookupError:
            errors.append(alert_conf_error(
                _('SLM_AUTOMATED_ALERTS[{}] is not a registered model label.')
                .format(alert)
            ))
            continue
        if not AlertModel.automated:
            errors.append(alert_conf_error(
                _('SLM_AUTOMATED_ALERTS[{}] is a non-automated alert type.')
                .format(alert)
            ))
            continue

        if not isinstance(AlertModel.objects.SUPPORTED_SIGNALS, dict):
            errors.append(alert_conf_error(
                _('{}.objects.SUPPORTED_SIGNALS must be a dictionary keyed '
                  'with `issue` and `rescind` signal lists that are supported.'
                  )
                .format(AlertModel.__name__)
            ))
            continue

        def check_signals(signal_type):
            for signal in config.get(signal_type, []):
                try:
                    signal = import_string(signal)
                    if not isinstance(signal, Signal):
                        errors.append(alert_conf_error(
                            _('SLM_AUTOMATED_ALERTS[{}][{}][{}] is not a '
                              'Signal').format(
                                alert, signal_type, signal_name(signal)
                            ),
                        ))
                except ImportError:
                    errors.append(alert_conf_error(
                        _('SLM_AUTOMATED_ALERTS[{}][{}] contains a non '
                          'existent trigger signal ({}).').format(
                            alert, signal_type, signal_name(signal)
                        )
                    ))
                    continue

                if signal not in AlertModel.objects.SUPPORTED_SIGNALS.get(
                    signal_type, []
                ):
                    errors.append(alert_conf_error(
                        _('SLM_AUTOMATED_ALERTS[{}][{}] contains an '
                          'unsupported signal ({}) for alerts of type '
                          '{}. Must be one of:\n{}').format(
                            alert,
                            signal_type,
                            signal_name(signal),
                            AlertModel,
                            pformat([
                                signal_name(sig)
                                for sig in
                                AlertModel.objects.SUPPORTED_SIGNALS[
                                    signal_type
                                ]
                            ])
                        )
                    ))

        check_signals('issue')
        check_signals('rescind')
    return errors


class SLMConfig(AppConfig):
    name = 'slm'

    # space is used as a workaround to alphabetically push SLM to the
    # top of the admin
    verbose_name = " SLM"

    def ready(self):

        from slm import signals as slm_signals
        from slm.models import Site, Alert
        from django.contrib.auth import get_user_model

        # don't remove these includes - they ensure signals are connected #####
        from slm.receivers import (
            event_loggers,  # register signal receivers that log events
        )
        from slm.receivers import cleanup, index, alerts
        #######################################################################

        @receiver(post_init, sender=Site)
        def site_init(sender, instance, **kwargs):
            # publishing may be tracked through a status update or if the
            # last_publish timestamp changes

            # an infinite recursion loop is triggered if you access a deferred
            # field in a model's init(). We guard against that case here, which
            # can happen when related fields are deleted. Such cases should
            # not involve a status update
            deferred = instance.get_deferred_fields()
            if 'status' not in deferred and 'last_publish' not in deferred:
                instance._slm_pre_status = instance.status
                instance._slm_last_publish = instance.last_publish
                if instance.pk is None:
                    instance._slm_pre_status = None
                    instance._slm_last_publish = None

        @receiver(post_save, sender=Site)
        def site_save(
            sender, instance, created, raw, using, update_fields, **kwargs
        ):
            if (
                hasattr(instance, '_slm_pre_status') and
                instance._slm_pre_status != instance.status
            ) or (
                hasattr(instance, '_slm_last_publish') and
                instance._slm_last_publish != instance.last_publish
            ):
                slm_signals.site_status_changed.send(
                    sender=self,
                    site=instance,
                    previous_status=instance._slm_pre_status,
                    new_status=instance.status
                )

        @receiver(post_save, sender=get_user_model())
        def user_save(
            sender, instance, created, raw, using, update_fields, **kwargs
        ):
            """Clear any relevant caches whenever a user is saved."""
            clear_caches()

        def alert_save(
            sender, instance, created, raw, using, update_fields, **kwargs
        ):
            if created:
                slm_signals.alert_issued.send(sender=sender, alert=instance)

        def cache_realalert(sender, instance, using, **kwargs):
            """
            Cache real alert instance onto the model because we wont be able
            to get it in post because it no longer exists.
            """
            #
            instance._slm_real_alert = instance.get_real_instance()

        def alert_delete(sender, instance, using, **kwargs):
            slm_signals.alert_cleared.send(
                sender=sender,
                alert=getattr(instance, '_slm_real_alert', instance)
            )

        for alert in Alert.objects.classes():
            post_save.connect(alert_save, sender=alert)
            pre_delete.connect(cache_realalert, sender=Alert)
            post_delete.connect(alert_delete, sender=Alert)

        @receiver(post_migrate)
        def populate_groups(**kwargs):
            from django.contrib.auth.models import Group, Permission
            for group_name, permissions in getattr(
                settings, 'SLM_DEFAULT_PERMISSION_GROUPS', {}
            ).items():
                group, created = Group.objects.get_or_create(name=group_name)
                if created:
                    group.permissions.set(
                        Permission.objects.filter(codename__in=permissions)
                    )
                    group.save()

        # load schemas into memory - this can take a few moments and requires
        # a live internet connection
        xsd_preload = getattr(
            settings,
            'SLM_PRELOAD_SCHEMAS',
            [geo for geo in GeodesyMLVersion]
        )
        if xsd_preload and not getattr(settings, 'SLM_MANAGEMENT_MODE', False):
            with tqdm(
                total=len(xsd_preload),
                desc='Loading',
                unit='schema',
                postfix={'xsd': None}
            ) as p_bar:
                for geo_version in xsd_preload:
                    p_bar.set_postfix({'xsd': str(geo_version)})
                    getattr(geo_version, 'schema')
                    p_bar.update(n=1)
