if (typeof slm === 'undefined' || slm == null) { var slm = {}; }

{% enums_to_js enums=enums raise_on_not_found=False symmetric_properties=True %}

SiteLogStatus.prototype.set = function (child) {
    if (
        this === SiteLogStatus.PUBLISHED ||
        this === SiteLogStatus.UPDATED ||
        this === SiteLogStatus.EMPTY
    ) {
        return child;
    }
    return this.merge(child);
};

SiteLogStatus.prototype.merge = function (sibling) {
    if (sibling !== null && sibling.value < this.value) {
        return sibling;
    }
    return this;
};

slm.LogEntryType = LogEntryType;
slm.SiteLogStatus = SiteLogStatus;
slm.SiteFileUploadStatus = SiteFileUploadStatus;
slm.AlertLevel = AlertLevel;
slm.SiteLogFormat = SiteLogFormat;
slm.SLMFileType = SLMFileType;
