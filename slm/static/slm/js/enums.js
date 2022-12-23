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
    }
}

class SiteLogStatus {
    
    static DORMANT = new SiteLogStatus(0, 'Dormant', 'slm-status-dormant', '#3D4543');
    static PENDING = new SiteLogStatus(1, 'Pending', 'slm-status-pending', '#913D88');
    static UPDATED = new SiteLogStatus(2, 'Updated', 'slm-status-updated', '#8D6708');
    static PUBLISHED = new SiteLogStatus(3, 'Published', 'slm-status-published', '#0F980F');
    static EMPTY = new SiteLogStatus(4, 'Empty', 'slm-status-empty', '#00000000');

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
            case 0:
                return SiteLogStatus.DORMANT;
            case 1:
                return SiteLogStatus.PENDING;
            case 2:
                return SiteLogStatus.UPDATED;
            case 3:
                return SiteLogStatus.PUBLISHED;
            case 4:
                return SiteLogStatus.EMPTY;
        }
    }
}

class SiteFileUploadStatus {
    
    static UNPUBLISHED = new SiteFileUploadStatus(0, 'Unpublished', 'slm-upload-unpublished', '#8D6708');
    static PUBLISHED = new SiteFileUploadStatus(1, 'Published', 'slm-upload-published', '#0F980F');
    static INVALID = new SiteFileUploadStatus(2, 'Invalid', 'slm-upload-invalid', '#8b0000');
    static WARNINGS = new SiteFileUploadStatus(3, 'Warnings', 'slm-upload-warnings', '#8D6708');
    static VALID = new SiteFileUploadStatus(4, 'Valid', 'slm-upload-valid', '#0F980F');

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
            case 0:
                return SiteFileUploadStatus.UNPUBLISHED;
            case 1:
                return SiteFileUploadStatus.PUBLISHED;
            case 2:
                return SiteFileUploadStatus.INVALID;
            case 3:
                return SiteFileUploadStatus.WARNINGS;
            case 4:
                return SiteFileUploadStatus.VALID;
        }
    }
}

class AlertLevel {
    
    static INFO = new AlertLevel(0, 'INFO', 'info');
    static WARNING = new AlertLevel(1, 'WARNING', 'warning');
    static ERROR = new AlertLevel(2, 'ERROR', 'danger');

    constructor(val, label, bootstrap) {
        this.val = val;
        this.label = label;
        this.bootstrap = bootstrap;
    }

    toString() {
        return this.label;
    }

    static get(val) {
        switch(val) {
            case 0:
                return AlertLevel.INFO;
            case 1:
                return AlertLevel.WARNING;
            case 2:
                return AlertLevel.ERROR;
        }
    }
}


class SiteLogFormat {
    
    static LEGACY = new SiteLogFormat(0, 'Legacy (ASCII)', 'bi bi-file-text');
    static GEODESY_ML = new SiteLogFormat(1, 'GeodesyML', 'bi bi-filetype-xml');
    static JSON = new SiteLogFormat(2, 'JSON', 'bi bi-filetype-json');

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
            case 0:
                return SiteLogFormat.LEGACY;
            case 1:
                return SiteLogFormat.GEODESY_ML;
            case 2:
                return SiteLogFormat.JSON;
        }
    }
}

class SLMFileType {
    
    static SITE_LOG = new SLMFileType(0, 'Site Log');
    static SITE_IMAGE = new SLMFileType(1, 'Site Image');
    static ATTACHMENT = new SLMFileType(2, 'Attachment');

    constructor(val, label) {
        this.val = val;
        this.label = label;
    }

    toString() {
        return this.label;
    }

    static get(val) {
        switch(val) {
            case 0:
                return SLMFileType.SITE_LOG;
            case 1:
                return SLMFileType.SITE_IMAGE;
            case 2:
                return SLMFileType.ATTACHMENT;
        }
    }
}

slm.LogEntryType = LogEntryType;
slm.SiteLogStatus = SiteLogStatus;
slm.SiteFileUploadStatus = SiteFileUploadStatus;
slm.AlertLevel = AlertLevel;
slm.SiteLogFormat = SiteLogFormat;
slm.SLMFileType = SLMFileType;
