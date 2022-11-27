if (typeof slm === 'undefined' || slm == null) { var slm = {}; }

class LogEntryType {
    
    static NEW_SITE = new LogEntryType(1, 'New Site', 'slm-log-new site');
    static ADD = new LogEntryType(2, 'Add', 'slm-log-add');
    static UPDATE = new LogEntryType(3, 'Update', 'slm-log-update');
    static DELETE = new LogEntryType(4, 'Delete', 'slm-log-delete');
    static PUBLISH = new LogEntryType(5, 'Publish', 'slm-log-publish');

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
        }
    }
}

class SiteLogStatus {
    
    static DORMANT = new SiteLogStatus(0, 'Dormant', 'slm-status-dormant', '#3D4543');
    static PENDING = new SiteLogStatus(1, 'Pending', 'slm-status-pending', '#913D88');
    static UPDATED = new SiteLogStatus(2, 'Updated', 'slm-status-updated', '#8D6708');
    static PUBLISHED = new SiteLogStatus(3, 'Published', 'slm-status-published', '#008000');
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

slm.LogEntryType = LogEntryType;
slm.SiteLogStatus = SiteLogStatus;
slm.AlertLevel = AlertLevel;
