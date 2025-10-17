if (typeof slm === 'undefined' || slm == null) { var slm = {}; }

class LogEntryType {
	
	static SITE_PROPOSED = new LogEntryType(1, "SITE_PROPOSED", "Site Proposed", "slm-log-site-proposed");
	static ADD = new LogEntryType(2, "ADD", "Add", "slm-log-add");
	static UPDATE = new LogEntryType(3, "UPDATE", "Update", "slm-log-update");
	static DELETE = new LogEntryType(4, "DELETE", "Delete", "slm-log-delete");
	static PUBLISH = new LogEntryType(5, "PUBLISH", "Publish", "slm-log-publish");
	static LOG_UPLOAD = new LogEntryType(6, "LOG_UPLOAD", "Log Upload", "slm-log-log-upload");
	static IMAGE_UPLOAD = new LogEntryType(7, "IMAGE_UPLOAD", "Image Upload", "slm-log-image-upload");
	static ATTACHMENT_UPLOAD = new LogEntryType(8, "ATTACHMENT_UPLOAD", "Attachment Upload", "slm-log-attachment-upload");
	static IMAGE_PUBLISH = new LogEntryType(9, "IMAGE_PUBLISH", "Image Published", "slm-log-image-published");
	static ATTACHMENT_PUBLISH = new LogEntryType(10, "ATTACHMENT_PUBLISH", "Attachment Published", "slm-log-attachment-published");
	static IMAGE_UNPUBLISH = new LogEntryType(11, "IMAGE_UNPUBLISH", "Image Unpublished", "slm-log-image-unpublished");
	static ATTACHMENT_UNPUBLISH = new LogEntryType(12, "ATTACHMENT_UNPUBLISH", "Attachment Unpublished", "slm-log-attachment-unpublished");
	static IMAGE_DELETE = new LogEntryType(13, "IMAGE_DELETE", "Image Deleted", "slm-log-image-deleted");
	static ATTACHMENT_DELETE = new LogEntryType(14, "ATTACHMENT_DELETE", "Attachment Deleted", "slm-log-attachment-deleted");
	static REVERT = new LogEntryType(15, "REVERT", "Revert", "slm-log-revert");
	
	constructor (value, name, label, css) {
		this.value = value;
		this.name = name;
		this.label = label;
		this.css = css;
	}
	
	static ciCompare(a, b) {
		return typeof a === 'string' && typeof b === 'string' ? a.localeCompare(b, undefined, { sensitivity: 'accent' }) === 0 : a === b;
	}
	
	toString() {
		return this.label;
	}
	
	static get(value) {
		if (value instanceof this) {
			return value;
		}
		
		for (const en of this) {
			if (en.value === value) {
				return en;
			}
		}
		for (const en of this) {
			if (this.ciCompare(en.name, value)) {
				return en;
			}
		}
		return null;
	}
	
	static [Symbol.iterator]() {
		return [LogEntryType.SITE_PROPOSED, LogEntryType.ADD, LogEntryType.UPDATE, LogEntryType.DELETE, LogEntryType.PUBLISH, LogEntryType.LOG_UPLOAD, LogEntryType.IMAGE_UPLOAD, LogEntryType.ATTACHMENT_UPLOAD, LogEntryType.IMAGE_PUBLISH, LogEntryType.ATTACHMENT_PUBLISH, LogEntryType.IMAGE_UNPUBLISH, LogEntryType.ATTACHMENT_UNPUBLISH, LogEntryType.IMAGE_DELETE, LogEntryType.ATTACHMENT_DELETE, LogEntryType.REVERT][Symbol.iterator]();
	}
}
class SiteLogStatus {
	
	static FORMER = new SiteLogStatus(1, "FORMER", "Former", "Site is no longer maintained and logs are not published.", "slm-status-former", "#3D4543");
	static PROPOSED = new SiteLogStatus(2, "PROPOSED", "Proposed", "This is a new Site that has never been published.", "slm-status-proposed", "#913D88");
	static UPDATED = new SiteLogStatus(3, "UPDATED", "Updated", "Site log or section has unpublished updates.", "slm-status-updated", "#0079AD");
	static PUBLISHED = new SiteLogStatus(4, "PUBLISHED", "Published", "Site log or section is published with no unpublished changes.", "slm-status-published", "#0D820D");
	static EMPTY = new SiteLogStatus(5, "EMPTY", "Empty", "Site log section is empty or deleted.", "slm-status-empty", "#D3D3D3");
	static SUSPENDED = new SiteLogStatus(6, "SUSPENDED", "Suspended", "Site has been temporarily suspended and does not appear in public data.", "slm-status-suspended", "#E0041A");
	
	constructor (value, name, label, help, css, color) {
		this.value = value;
		this.name = name;
		this.label = label;
		this.help = help;
		this.css = css;
		this.color = color;
	}
	
	static ciCompare(a, b) {
		return typeof a === 'string' && typeof b === 'string' ? a.localeCompare(b, undefined, { sensitivity: 'accent' }) === 0 : a === b;
	}
	
	toString() {
		return this.label;
	}
	
	static get(value) {
		if (value instanceof this) {
			return value;
		}
		
		for (const en of this) {
			if (en.value === value) {
				return en;
			}
		}
		for (const en of this) {
			if (this.ciCompare(en.name, value)) {
				return en;
			}
		}
		return null;
	}
	
	static [Symbol.iterator]() {
		return [SiteLogStatus.FORMER, SiteLogStatus.PROPOSED, SiteLogStatus.UPDATED, SiteLogStatus.PUBLISHED, SiteLogStatus.EMPTY, SiteLogStatus.SUSPENDED][Symbol.iterator]();
	}
}
class AlertLevel {
	
	static NOTICE = new AlertLevel(1, "NOTICE", "NOTICE", "slm-alert-notice", "#12CAF0");
	static WARNING = new AlertLevel(2, "WARNING", "WARNING", "slm-alert-warning", "#E3AA00");
	static ERROR = new AlertLevel(3, "ERROR", "ERROR", "slm-alert-error", "#DD3444");
	
	constructor (value, name, label, css, color) {
		this.value = value;
		this.name = name;
		this.label = label;
		this.css = css;
		this.color = color;
	}
	
	static ciCompare(a, b) {
		return typeof a === 'string' && typeof b === 'string' ? a.localeCompare(b, undefined, { sensitivity: 'accent' }) === 0 : a === b;
	}
	
	toString() {
		return this.name;
	}
	
	static get(value) {
		if (value instanceof this) {
			return value;
		}
		
		for (const en of this) {
			if (en.value === value) {
				return en;
			}
		}
		for (const en of this) {
			if (this.ciCompare(en.name, value)) {
				return en;
			}
		}
		for (const en of this) {
			if (en.label === value) {
				return en;
			}
		}
		return null;
	}
	
	static [Symbol.iterator]() {
		return [AlertLevel.NOTICE, AlertLevel.WARNING, AlertLevel.ERROR][Symbol.iterator]();
	}
}
class SiteFileUploadStatus {
	
	static UNPUBLISHED = new SiteFileUploadStatus(1, "UNPUBLISHED", "Unpublished File", "The file is pending moderation before it will be made public.", "slm-upload-unpublished file", "#0079AD");
	static PUBLISHED = new SiteFileUploadStatus(2, "PUBLISHED", "Published File", "The file is published and is publicly available as an attachment to the site.", "slm-upload-published file", "#0D820D");
	static INVALID = new SiteFileUploadStatus(3, "INVALID", "Invalid Site Log", "The file did not pass validation.", "slm-upload-invalid site log", "#8b0000");
	static WARNINGS = new SiteFileUploadStatus(4, "WARNINGS", "Warnings Site Log", "The file is valid but has some warnings.", "slm-upload-warnings site log", "#E3AA00");
	static VALID = new SiteFileUploadStatus(5, "VALID", "Valid Site Log", "The file is valid.", "slm-upload-valid site log", "#0D820D");
	
	constructor (value, name, label, help, css, color) {
		this.value = value;
		this.name = name;
		this.label = label;
		this.help = help;
		this.css = css;
		this.color = color;
	}
	
	static ciCompare(a, b) {
		return typeof a === 'string' && typeof b === 'string' ? a.localeCompare(b, undefined, { sensitivity: 'accent' }) === 0 : a === b;
	}
	
	toString() {
		return this.label;
	}
	
	static get(value) {
		if (value instanceof this) {
			return value;
		}
		
		for (const en of this) {
			if (en.value === value) {
				return en;
			}
		}
		for (const en of this) {
			if (this.ciCompare(en.name, value)) {
				return en;
			}
		}
		return null;
	}
	
	static [Symbol.iterator]() {
		return [SiteFileUploadStatus.UNPUBLISHED, SiteFileUploadStatus.PUBLISHED, SiteFileUploadStatus.INVALID, SiteFileUploadStatus.WARNINGS, SiteFileUploadStatus.VALID][Symbol.iterator]();
	}
}
class SiteLogFormat {
	
	static LEGACY = new SiteLogFormat(1, "LEGACY", "Legacy (ASCII)", "text/plain", "bi bi-file-text", "log", ["text", "txt", "legacy", "sitelog"], [], "log");
	static GEODESY_ML = new SiteLogFormat(2, "GEODESY_ML", "GeodesyML", "application/xml", "bi bi-filetype-xml", "xml", ["xml", "gml"], [], "xml");
	static JSON = new SiteLogFormat(3, "JSON", "JSON", "application/json", "bi bi-filetype-json", "json", ["json", "js"], [], "json");
	static ASCII_9CHAR = new SiteLogFormat(4, "ASCII_9CHAR", "ASCII (9-Char)", "text/plain", "bi bi-file-text", "log", ["text", "txt", "9char", "sitelog"], "[(1, 'Legacy (ASCII)')]", "log");
	
	constructor (value, name, label, mimetype, icon, ext, alts, supersedes, suffix) {
		this.value = value;
		this.name = name;
		this.label = label;
		this.mimetype = mimetype;
		this.icon = icon;
		this.ext = ext;
		this.alts = alts;
		this.supersedes = supersedes;
		this.suffix = suffix;
	}
	
	static ciCompare(a, b) {
		return typeof a === 'string' && typeof b === 'string' ? a.localeCompare(b, undefined, { sensitivity: 'accent' }) === 0 : a === b;
	}
	
	toString() {
		return this.label;
	}
	
	static get(value) {
		if (value instanceof this) {
			return value;
		}
		
		for (const en of this) {
			if (en.value === value) {
				return en;
			}
		}
		for (const en of this) {
			if (this.ciCompare(en.name, value)) {
				return en;
			}
		}
		return null;
	}
	
	static [Symbol.iterator]() {
		return [SiteLogFormat.LEGACY, SiteLogFormat.GEODESY_ML, SiteLogFormat.JSON, SiteLogFormat.ASCII_9CHAR][Symbol.iterator]();
	}
}
class SLMFileType {
	
	static SITE_LOG = new SLMFileType(1, "SITE_LOG", "Site Log", "log");
	static SITE_IMAGE = new SLMFileType(2, "SITE_IMAGE", "Site Image", "image");
	static ATTACHMENT = new SLMFileType(3, "ATTACHMENT", "Attachment", "attachment");
	
	constructor (value, name, label, type) {
		this.value = value;
		this.name = name;
		this.label = label;
		this.type = type;
	}
	
	static ciCompare(a, b) {
		return typeof a === 'string' && typeof b === 'string' ? a.localeCompare(b, undefined, { sensitivity: 'accent' }) === 0 : a === b;
	}
	
	toString() {
		return this.label;
	}
	
	static get(value) {
		if (value instanceof this) {
			return value;
		}
		
		for (const en of this) {
			if (en.value === value) {
				return en;
			}
		}
		for (const en of this) {
			if (this.ciCompare(en.name, value)) {
				return en;
			}
		}
		for (const en of this) {
			if (en.type === value) {
				return en;
			}
		}
		return null;
	}
	
	static [Symbol.iterator]() {
		return [SLMFileType.SITE_LOG, SLMFileType.SITE_IMAGE, SLMFileType.ATTACHMENT][Symbol.iterator]();
	}
}


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
