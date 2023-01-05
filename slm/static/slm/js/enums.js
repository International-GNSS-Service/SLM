if (typeof slm === 'undefined' || slm == null) { var slm = {}; }

class LogEntryType {
    
    static NEW_SITE = new LogEntryType(1, 'New Site', 'slm-log-new-site');
    static ADD = new LogEntryType(2, 'Add', 'slm-log-add');
    static UPDATE = new LogEntryType(3, 'Update', 'slm-log-update');
    static DELETE = new LogEntryType(4, 'Delete', 'slm-log-delete');
    static PUBLISH = new LogEntryType(5, 'Publish', 'slm-log-publish');
    static LOG_UPLOAD = new LogEntryType(6, 'Log Upload', 'slm-log-log-upload');
    static FILE_UPLOAD = new LogEntryType(7, 'File Upload', 'slm-log-file-upload');

    constructor(val, label, css) {
        this.val = val;
        this.label = label;
        this.css = css;
    }

    toString() {
        return this.label;
    }

    static get(val) {
        switch(val) {
            case 1:
                return LogEntryType.NEW_SITE;
            case 2:
                return LogEntryType.ADD;
            case 3:
                return LogEntryType.UPDATE;
            case 4:
                return LogEntryType.DELETE;
            case 5:
                return LogEntryType.PUBLISH;
            case 6:
                return LogEntryType.LOG_UPLOAD;
            case 7:
                return LogEntryType.FILE_UPLOAD;
        }
        return null;
    }
}

class SiteLogStatus {
    
    static DORMANT = new SiteLogStatus(1, 'Dormant', 'slm-status-dormant', '#3D4543');
    static NASCENT = new SiteLogStatus(2, 'Nascent', 'slm-status-nascent', '#913D88');
    static UPDATED = new SiteLogStatus(3, 'Updated', 'slm-status-updated', '#0084BD');
    static PUBLISHED = new SiteLogStatus(4, 'Published', 'slm-status-published', '#0F980F');
    static EMPTY = new SiteLogStatus(5, 'Empty', 'slm-status-empty', '#D3D3D3');

    constructor(val, label, css, color) {
        this.val = val;
        this.label = label;
        this.css = css;
        this.color = color;
    }

    toString() {
        return this.label;
    }

    merge(sibling) {
        if (sibling !== null && sibling.val < this.val) {
            return sibling;
        }
        return this;
    }

    set(child) {
        if (
            this === SiteLogStatus.PUBLISHED ||
            this === SiteLogStatus.UPDATED ||
            this === SiteLogStatus.EMPTY
        ) {
            return child;
        }
        return this.merge(child);
    }

    static get(val) {
        switch(val) {
            case 1:
                return SiteLogStatus.DORMANT;
            case 2:
                return SiteLogStatus.NASCENT;
            case 3:
                return SiteLogStatus.UPDATED;
            case 4:
                return SiteLogStatus.PUBLISHED;
            case 5:
                return SiteLogStatus.EMPTY;
        }
        return null;
    }
}

class SiteFileUploadStatus {
    
    static UNPUBLISHED = new SiteFileUploadStatus(1, 'Unpublished File', 'slm-upload-unpublished file', '#0084BD');
    static PUBLISHED = new SiteFileUploadStatus(2, 'Published File', 'slm-upload-published file', '#0F980F');
    static INVALID = new SiteFileUploadStatus(3, 'Invalid Site Log', 'slm-upload-invalid site log', '#8b0000');
    static WARNINGS = new SiteFileUploadStatus(4, 'Warnings Site Log', 'slm-upload-warnings site log', '#E3AA00');
    static VALID = new SiteFileUploadStatus(5, 'Valid Site Log', 'slm-upload-valid site log', '#0F980F');

    constructor(val, label, css, color) {
        this.val = val;
        this.label = label;
        this.css = css;
        this.color = color;
    }

    toString() {
        return this.label;
    }

    static get(val) {
        switch(val) {
            case 1:
                return SiteFileUploadStatus.UNPUBLISHED;
            case 2:
                return SiteFileUploadStatus.PUBLISHED;
            case 3:
                return SiteFileUploadStatus.INVALID;
            case 4:
                return SiteFileUploadStatus.WARNINGS;
            case 5:
                return SiteFileUploadStatus.VALID;
        }
        return null;
    }
}

class AlertLevel {
    
    static NOTICE = new AlertLevel(1, 'NOTICE', '#12CAF0', 'slm-alert-notice');
    static WARNING = new AlertLevel(2, 'WARNING', '#E3AA00', 'slm-alert-warning');
    static ERROR = new AlertLevel(3, 'ERROR', '#DD3444', 'slm-alert-error');

    constructor(val, label, color, css) {
        this.val = val;
        this.label = label;
        this.color = color;
        this.css = css;
    }

    toString() {
        return this.label;
    }

    static get(val) {
        switch(val) {
            case 1:
                return AlertLevel.NOTICE;
            case 2:
                return AlertLevel.WARNING;
            case 3:
                return AlertLevel.ERROR;
        }
        return null;
    }
}


class SiteLogFormat {
    
    static LEGACY = new SiteLogFormat(1, 'Legacy (ASCII)', 'bi bi-file-text');
    static GEODESY_ML = new SiteLogFormat(2, 'GeodesyML', 'bi bi-filetype-xml');
    static JSON = new SiteLogFormat(3, 'JSON', 'bi bi-filetype-json');

    constructor(val, label, icon) {
        this.val = val;
        this.label = label;
        this.icon = icon;
    }

    toString() {
        return this.label;
    }

    static get(val) {
        switch(val) {
            case 1:
                return SiteLogFormat.LEGACY;
            case 2:
                return SiteLogFormat.GEODESY_ML;
            case 3:
                return SiteLogFormat.JSON;
        }
        return null;
    }
}

class SLMFileType {
    
    static SITE_LOG = new SLMFileType(1, 'Site Log');
    static SITE_IMAGE = new SLMFileType(2, 'Site Image');
    static ATTACHMENT = new SLMFileType(3, 'Attachment');

    constructor(val, label) {
        this.val = val;
        this.label = label;
    }

    toString() {
        return this.label;
    }

    static get(val) {
        switch(val) {
            case 1:
                return SLMFileType.SITE_LOG;
            case 2:
                return SLMFileType.SITE_IMAGE;
            case 3:
                return SLMFileType.ATTACHMENT;
        }
        return null;
    }
}

slm.LogEntryType = LogEntryType;
slm.SiteLogStatus = SiteLogStatus;
slm.SiteFileUploadStatus = SiteFileUploadStatus;
slm.AlertLevel = AlertLevel;
slm.SiteLogFormat = SiteLogFormat;
slm.SLMFileType = SLMFileType;
