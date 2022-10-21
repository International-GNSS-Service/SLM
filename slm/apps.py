from django.apps import AppConfig
from django.apps import apps
from django.db.models.signals import (
    pre_save,
    post_save
)
from slm import signals as slm_signals
from django.db.models import Q, Max
from ipware import get_client_ip


class SLMConfig(AppConfig):
    name = 'slm'

    # space is used as a workaround to alphabetically push SLM to the
    # top of the admin
    verbose_name = " SLM"

    def ready(self):
        from slm import receivers  # import our default receivers
        from slm.defines import LogEntryType
        from slm.models import (
            Site,
            SiteSection,
            SiteSubSection,
            LogEntry
        )
        from django.contrib.contenttypes.models import ContentType

        def validate_updates(sender, instance, raw, using, update_fields, **kwargs):
            pass

        def handle_section_update(sender, instance, created, raw, using, update_fields, **kwargs):
            """
            Handle an update to a SiteLog Section.

            :param sender: The model class.
            :param instance: The actual instance being saved.
            :param created: A boolean; True if a new record was created.
            :param raw: A boolean; True if the model is saved exactly as presented (i.e. when loading a fixture). One should
                not query/modify other records in the database as the database might not be in a consistent state yet
            :param using: The database alias being used.
            :param update_fields: The set of fields to update as passed to Model.save(), or None if update_fields was not
                passed to save().
            :param kwargs:
            :return:
            """
            if sender is Site and created:
                LogEntry.objects.create(
                    type=LogEntryType.NEW_SITE,
                    user=instance.last_user,
                    site=instance,
                    site_log_object=instance,
                    epoch=instance.created,
                    ip=getattr(instance, '_ip', None)
                )
            elif issubclass(sender, SiteSection):
                if getattr(instance, '_flag_update', False):
                    instance.site.update_status(save=True)
                    return

                if instance.published and getattr(instance, '_publisher', None):
                    entry_type = LogEntryType.PUBLISH
                else:
                    entry_type = LogEntryType.UPDATE

                    if issubclass(sender, SiteSubSection):
                        if instance.is_deleted:
                            entry_type = LogEntryType.DELETE
                        elif not sender.objects.filter(
                                site=instance.site,
                                subsection=instance.subsection,
                                edited__lt=instance.edited
                        ).exists():
                            entry_type = LogEntryType.ADD

                if entry_type == LogEntryType.UPDATE:
                    # since we only allow one instance capturing all unpublished edits and we rely on log entries for
                    # diffing we have to update the data epochs accordingly - oh the joys of denormalized data!
                    update_q = (
                            Q(site=instance.site) &
                            Q(site_log_type=ContentType.objects.get_for_model(instance)) &
                            Q(site_log_id=instance.id)
                    )
                    update_horizon = LogEntry.objects.select_for_update().filter(
                        update_q & ~Q(type=LogEntryType.UPDATE)
                    ).aggregate(Max('timestamp'))['timestamp__max']
                    if update_horizon:
                        update_q &= Q(timestamp__gt=update_horizon)
                    LogEntry.objects.filter(update_q).update(epoch=instance.edited)

                entry = LogEntry.objects.create(
                    type=entry_type,
                    user=getattr(instance, '_publisher', None) or instance.editor,
                    site=instance.site,
                    site_log_object=instance,
                    epoch=instance.edited,
                    ip=getattr(instance, '_ip', None)
                )

                if entry.type == LogEntryType.PUBLISH:
                    instance.site.last_publish = entry.timestamp
                else:
                    instance.site.last_update = entry.timestamp

                instance.site.last_user = entry.user
                instance.site.update_status(save=True)

        post_save.connect(handle_section_update, Site)
        for model_class in apps.get_models():
            if issubclass(model_class, SiteSection):
                post_save.connect(handle_section_update, model_class)
                pre_save.connect(validate_updates, model_class)

