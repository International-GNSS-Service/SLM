if (typeof slm === 'undefined' || slm == null) { var slm = {}; }

class LogEntryType {
    {% for entry in LogEntryType %}
    static {{entry.name}} = new LogEntryType({{entry.value}}, '{{entry.label}}', '{{entry.css}}');{% endfor %}

    constructor(val, label, css) {
        this.val = val;
        this.label = label;
        this.css = css;
    }

    toString() {
        return this.label;
    }

    static get(val) {
        switch(val) {{% for entry in LogEntryType %}
            case {{entry.value}}:
                return LogEntryType.{{entry.name}};{% endfor %}
        }
        return null;
    }
}

class SiteLogStatus {
    {% for status in SiteLogStatus %}
    static {{status.name}} = new SiteLogStatus({{status.value}}, '{{status.label}}', '{{status.css}}', '{{status.color}}');{% endfor %}

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
        switch(val) {{% for status in SiteLogStatus %}
            case {{status.value}}:
                return SiteLogStatus.{{status.name}};{% endfor %}
        }
        return null;
    }
}

class SiteFileUploadStatus {
    {% for status in SiteFileUploadStatus %}
    static {{status.name}} = new SiteFileUploadStatus({{status.value}}, '{{status.label}}', '{{status.css}}', '{{status.color}}');{% endfor %}

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
        switch(val) {{% for status in SiteFileUploadStatus %}
            case {{status.value}}:
                return SiteFileUploadStatus.{{status.name}};{% endfor %}
        }
        return null;
    }
}

class AlertLevel {
    {% for level in AlertLevel %}
    static {{level.name}} = new AlertLevel({{level.value}}, '{{level.label}}', '{{level.color}}', '{{level.css}}');{% endfor %}

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
        switch(val) {{% for level in AlertLevel %}
            case {{level.value}}:
                return AlertLevel.{{level.name}};{% endfor %}
        }
        return null;
    }
}


class SiteLogFormat {
    {% for format in SiteLogFormat %}
    static {{format.name}} = new SiteLogFormat({{format.value}}, '{{format.label}}', '{{format.icon}}');{% endfor %}

    constructor(val, label, icon) {
        this.val = val;
        this.label = label;
        this.icon = icon;
    }

    toString() {
        return this.label;
    }

    static get(val) {
        switch(val) {{% for format in SiteLogFormat %}
            case {{format.value}}:
                return SiteLogFormat.{{format.name}};{% endfor %}
        }
        return null;
    }
}

class SLMFileType {
    {% for typ in SLMFileType %}
    static {{typ.name}} = new SLMFileType({{typ.value}}, '{{typ.label}}');{% endfor %}

    constructor(val, label) {
        this.val = val;
        this.label = label;
    }

    toString() {
        return this.label;
    }

    static get(val) {
        switch(val) {{% for typ in SLMFileType %}
            case {{typ.value}}:
                return SLMFileType.{{typ.name}};{% endfor %}
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
