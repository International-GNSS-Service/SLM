"""
SLM Specific Configuration parameters go here.
"""
from slm.defines import SiteLogStatus


SLM_STATUS_COLORS = {
    SiteLogStatus.DORMANT: '#3D4543',
    SiteLogStatus.PENDING: '#913D88',
    SiteLogStatus.UPDATED: '#8D6708',
    SiteLogStatus.PUBLISHED: '#008000',
}
