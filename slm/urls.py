from datetime import datetime

from django.urls import path, register_converter
from slm.api.edit import views as edit_views
from slm.api.public import views as public_views
from slm.views import (
    AlertsView,
    AlertView,
    DownloadView,
    EditView,
    IndexView,
    LogView,
    NewSiteView,
    SLMView,
    StationAlertsView,
    StationReviewView,
    UploadView,
    UserActivityLogView,
    UserProfileView,
    download_site_attachment,
)

api = {
    'edit': {
        'serializer_module': 'slm.api.edit.serializers',
        'endpoints': [
            ('stations', edit_views.StationListViewSet),
            ('profile', edit_views.UserProfileViewSet),
            ('download', edit_views.SiteLogDownloadViewSet),
            (
                'files/(?P<site>[^/.]+)',
                edit_views.SiteFileUploadViewSet,
                'files'
            ),
            ('siteform', edit_views.SiteFormViewSet),
            ('siteidentification', edit_views.SiteIdentificationViewSet),
            ('sitelocation', edit_views.SiteLocationViewSet),
            ('sitereceiver', edit_views.SiteReceiverViewSet),
            ('siteantenna', edit_views.SiteAntennaViewSet),
            ('sitesurveyedlocalties', edit_views.SiteSurveyedLocalTiesViewSet),
            ('sitefrequencystandard', edit_views.SiteFrequencyStandardViewSet),
            ('sitecollocation', edit_views.SiteCollocationViewSet),
            ('sitehumiditysensor', edit_views.SiteHumiditySensorViewSet),
            ('sitepressuresensor', edit_views.SitePressureSensorViewSet),
            ('sitetemperaturesensor', edit_views.SiteTemperatureSensorViewSet),
            (
                'sitewatervaporradiometer',
                edit_views.SiteWaterVaporRadiometerViewSet
            ),
            (
                'siteotherinstrumentation',
                edit_views.SiteOtherInstrumentationViewSet
            ),
            (
                'siteradiointerferences',
                edit_views.SiteRadioInterferencesViewSet
            ),
            ('sitemultipathsources', edit_views.SiteMultiPathSourcesViewSet),
            (
                'sitesignalobstructions',
                edit_views.SiteSignalObstructionsViewSet
            ),
            (
                'sitelocalepisodiceffects',
                edit_views.SiteLocalEpisodicEffectsViewSet
            ),
            (
                'siteoperationalcontact',
                edit_views.SiteOperationalContactViewSet
            ),
            ('siteresponsibleagency', edit_views.SiteResponsibleAgencyViewSet),
            ('sitemoreinformation', edit_views.SiteMoreInformationViewSet),
            ('logentries', edit_views.LogEntryViewSet),
            ('alerts', edit_views.AlertViewSet),
            ('request_review', edit_views.ReviewRequestView),
            ('reject_updates', edit_views.RejectUpdatesView),
        ]
    },
    'public': {
        'serializer_module': 'slm.api.public.serializers',
        'endpoints': [
            ('stations', public_views.StationListViewSet),
            ('download', public_views.SiteLogDownloadViewSet),
            ('files', public_views.SiteFileUploadViewSet)
        ]
    },
}


class SiteLogFormatConverter:
    regex = '(legacy)|(gml)'
    placeholder = 'legacy'

    def to_python(self, value):
        return value

    def to_url(self, value):
        return value


class StationConverter:
    regex = '[0-9a-zA-Z]{9}'
    placeholder = 'AAAAAAAAA'

    def to_python(self, value):
        return value

    def to_url(self, value):
        return value


class DateTimeConverter:
    regex = r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[.]\d{3,6}'
    placeholder = '2022-06-20T01:49:04.566687'

    def to_python(self, value: str) -> datetime:
        print(value)
        return datetime.fromisoformat(value)

    def to_url(self, value: datetime) -> str:
        if isinstance(value, str):
            return value
        return value.isoformat()


register_converter(SiteLogFormatConverter, 'format')
register_converter(StationConverter, 'station')
register_converter(DateTimeConverter, "datetime")


app_name = 'slm'

urlpatterns = [
    path('', IndexView.as_view(), name='home'),
    path('edit/<station:station>', EditView.as_view(), name='edit'),
    path(
        'edit/<station:station>/<str:section>',
        EditView.as_view(),
        name='edit'
    ),
    path('newsite/', NewSiteView.as_view(), name='new_site'),
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('alerts/', AlertsView.as_view(), name='alerts'),
    path(
        'alerts/<station:station>',
        StationAlertsView.as_view(),
        name='alerts'
    ),
    path('upload/<station:station>', UploadView.as_view(), name='upload'),
    path(
        'upload/<station:station>/<int:file>',
        UploadView.as_view(),
        name='upload'
    ),
    path(
        'download/<station:station>',
        DownloadView.as_view(),
        name='download'
    ),
    path(
        'download/<station:station>/<format:format>',
        DownloadView.as_view(),
        name='download'
    ),
    path(
        'review/<station:station>',
        StationReviewView.as_view(),
        name='review'
    ),
    path(
        'review/<station:station>/<datetime:epoch>',
        StationReviewView.as_view(),
        name='review'
    ),
    path('log/<station:station>', LogView.as_view(), name='log'),
    path(
        'about/',
        SLMView.as_view(template_name='slm/about.html'),
        name='about'
    ),
    path('help/', SLMView.as_view(template_name='slm/help.html'), name='help'),
    path('activity/', UserActivityLogView.as_view(), name='user_activity'),
    path(
        'activity/<int:log_user>',
        UserActivityLogView.as_view(),
        name='user_activity'
    ),
    path(
        'files/<station:site>/<int:pk>',
        download_site_attachment,
        name='download_attachment'
    ),
    path(
        'files/<station:site>/<int:pk>/thumbnail',
        download_site_attachment,
        name='download_attachment_thumbnail',
        kwargs={'thumbnail': True}
    ),
    path(
        'alert/<int:alert>',
        AlertView.as_view(),
        name='alert',
    )
]
