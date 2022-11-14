"""
The Site Log models contain edit histories and a tree-like structure that
make complex queries (potentially) very slow. To remedy this the best and
really only option is to denormalize the data. All searchable site log fields
should be defined and indexed here.

Think of this record as a Materialized View that's defined in code to make
it RDBMS independent.

Denormalization introduces the potential for data inconsistency. If updates are
published and a corresponding SiteRecord is not created, search results will be
incorrect. This will not however break editing or site log serialization. In
the context of the rest of the software - this table should be treated as
a read-only index.

Extensions:

Extending software may want to include or change search fields. To do this a
new SiteRecord model should be created that extends from AbstractSiteRecord.
In settings the SLM_SITE_RECORD setting should be updated to:
'<app_label>.<model_class>'. For instance, the default is:

.. code-block:

    SLM_SITE_RECORD = 'slm.DefaultSiteRecord'

SiteRecord is never used directly in software, like with Django's swappable
user model, use a function that returns the configured model type:

.. code-block:

    from slm.models import get_record_model
    get_record_model()

"""
from django.db import models
from slm.models.sitelog import Site
from slm.defines import SiteLogStatus
from django_enum import EnumField


class AbstractSiteRecord(models.Model):

    site = models.ForeignKey(Site, on_delete=models.CASCADE, null=False)

    # the point in time at which this record begins being valid
    begin = models.DateTimeField(null=True, db_index=True)

    # the point in time at which this record stops being valid
    end = models.DateTimeField(null=True, db_index=True)

    status = EnumField(SiteLogStatus, null=False, db_index=True)

    class Meta:
        abstract = True
        ordering = ('-begin',)
        index_together = (('begin', 'end'), ('site', 'begin', 'end'),)
        unique_together = (('site', 'begin'), ('site', 'end'))


class DefaultSiteRecord(AbstractSiteRecord):
    pass
