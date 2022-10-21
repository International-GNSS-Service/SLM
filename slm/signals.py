
from django import dispatch

site_published = dispatch.Signal(providing_args=['site', 'user'])

review_requested = dispatch.Signal(providing_args=['request'])
changes_rejected = dispatch.Signal(providing_args=['request', 'rejecter'])

alert_issued = dispatch.Signal(providing_args=['alert', 'issuer'])
alert_cleared = dispatch.Signal(providing_args=['alert', 'clearer'])
