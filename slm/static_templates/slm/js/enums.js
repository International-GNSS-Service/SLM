if (typeof slm === 'undefined' || slm == null) { var slm = {}; }

{% enums_to_js enums=enums raise_on_not_found=False %}

slm.LogEntryType = LogEntryType;
slm.SiteLogStatus = SiteLogStatus;
slm.SiteFileUploadStatus = SiteFileUploadStatus;
slm.AlertLevel = AlertLevel;
slm.SiteLogFormat = SiteLogFormat;
slm.SLMFileType = SLMFileType;
