from django.dispatch import receiver
from slm import signals as slm_signals
from django.core.mail import send_mail
from django.template.loader import get_template
from django.template import Context
from django.contrib.sites.models import Site as DjangoSite
from django.utils.translation import gettext as _
from smtplib import SMTPException
from django.conf import settings
import logging


logger = logging.getLogger(__name__)


@receiver(slm_signals.review_requested)
def send_review_request_emails(sender, request, **kwargs):
    text = get_template('slm/emails/review_requested.txt')
    html = get_template('slm/emails/review_requested.html')
    context = {
        'user': request.requester,
        'site': request.site
    }
    try:
        send_mail(
            subject=f'{_("Site Log Review Requested:")} {request.site.name}',
            from_email=getattr(
                settings.DEFAULT_FROM_EMAIL,
                f'noreply@{DjangoSite.objects.first().domain}'
            ),
            message=text.render(context),
            recipient_list=(
                list(request.site.moderators.emails_ok()) +
                list(request.site.editors.emails_ok())
            ),
            fail_silently=False,
            html_message=html.render(context)
        )
    except SMTPException as smtp_exc:
        logger.exception(smtp_exc)


@receiver(slm_signals.changes_rejected)
def send_changes_rejected_emails(sender, request, rejecter, **kwargs):
    text = get_template('slm/emails/changes_rejected.txt')
    html = get_template('slm/emails/changes_rejected.html')
    context = {
        'rejecter': rejecter,
        'site': request.site,
        'requester': request.requester
    }
    try:
        send_mail(
            subject=f'{_("Site Log Changes Rejected:")} {request.site.name}',
            from_email=getattr(
                settings.DEFAULT_FROM_EMAIL,
                f'noreply@{DjangoSite.objects.first().domain}'
            ),
            message=text.render(context),
            recipient_list=(
                list(request.site.moderators.emails_ok()) +
                list(request.site.editors.emails_ok())
            ),
            fail_silently=False,
            html_message=html.render(context)
        )
    except SMTPException as smtp_exc:
        logger.exception(smtp_exc)
