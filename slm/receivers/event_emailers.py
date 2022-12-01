"""
Signal handlers for signals that result in emails.
"""
from django.dispatch import receiver
from slm import signals as slm_signals
from django.core.mail import send_mail
from django.template.loader import get_template
from django.contrib.sites.models import Site as DjangoSite
from django.utils.translation import gettext as _
from smtplib import SMTPException
from django.conf import settings
import logging


logger = logging.getLogger(__name__)


@receiver(slm_signals.review_requested)
def send_review_request_emails(sender, review_request, request, **kwargs):
    """
    Send a review requested email to all moderators of the site and all editors
    of the site. (Email thread is started between moderators and editors)
    """
    text = get_template('slm/emails/review_requested.txt')
    html = get_template('slm/emails/review_requested.html')
    context = {
        'user': review_request.requester,
        'site': review_request.site
    }

    try:
        html_ok = not (
            review_request.site.moderators.emails_ok(html=False).count()
            or
            review_request.site.editors.emails_ok(html=False).count()
        )

        send_mail(
            subject=f'{_("Site Log Review Requested:")} '
                    f'{review_request.site.name}',
            from_email=getattr(
                settings,
                'DEFAULT_FROM_EMAIL',
                f'noreply@{DjangoSite.objects.first().domain}'
            ),
            message=text.render(context),
            recipient_list=(
                [
                    user.email
                    for user in review_request.site.moderators.emails_ok()
                ]
                +
                [
                    user.email
                    for user in review_request.site.editors.emails_ok()
                ]
            ),
            fail_silently=False,
            html_message=html.render(context) if html_ok else None
        )
        logger.info(
            'Sent review request email for %s',
            review_request.site.name
        )
    except SMTPException as smtp_exc:
        logger.exception(smtp_exc)


@receiver(slm_signals.changes_rejected)
def send_changes_rejected_emails(
        sender,
        review_request,
        request,
        rejecter,
        **kwargs
):
    """
    Send a change rejected email to all editors of the site.
    """
    text = get_template('slm/emails/changes_rejected.txt')
    html = get_template('slm/emails/changes_rejected.html')
    context = {
        'rejecter': rejecter,
        'site': review_request.site,
        'requester': review_request.requester
    }
    try:
        html_ok = not (
            review_request.site.moderators.emails_ok(html=False).count()
            or
            review_request.site.editors.emails_ok(html=False).count()
        )

        send_mail(
            subject=f'{_("Site Log Changes Rejected:")} '
                    f'{review_request.site.name}',
            from_email=getattr(
                settings,
                'DEFAULT_FROM_EMAIL',
                f'noreply@{DjangoSite.objects.first().domain}'
            ),
            message=text.render(context),
            recipient_list=(
                [
                    user.email
                    for user in review_request.site.moderators.emails_ok()
                ]
                +
                [
                    user.email
                    for user in review_request.site.editors.emails_ok()
                ]
            ),
            fail_silently=False,
            html_message=html.render(context) if html_ok else None
        )
        logger.info(
            'Sent changes rejected for %s',
            review_request.site.name
        )
    except SMTPException as smtp_exc:
        logger.exception(smtp_exc)
