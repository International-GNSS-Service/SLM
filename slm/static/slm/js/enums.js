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
	
	toString() {
		return this.label;
	}
	
	static get(value) {
		switch(value) {
			case 1:
				return LogEntryType.SITE_PROPOSED;
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
				return LogEntryType.IMAGE_UPLOAD;
			case 8:
				return LogEntryType.ATTACHMENT_UPLOAD;
			case 9:
				return LogEntryType.IMAGE_PUBLISH;
			case 10:
				return LogEntryType.ATTACHMENT_PUBLISH;
			case 11:
				return LogEntryType.IMAGE_UNPUBLISH;
			case 12:
				return LogEntryType.ATTACHMENT_UNPUBLISH;
			case 13:
				return LogEntryType.IMAGE_DELETE;
			case 14:
				return LogEntryType.ATTACHMENT_DELETE;
			case 15:
				return LogEntryType.REVERT;
		}
		switch(value) {
			case "SITE_PROPOSED":
				return LogEntryType.SITE_PROPOSED;
			case "ADD":
				return LogEntryType.ADD;
			case "UPDATE":
				return LogEntryType.UPDATE;
			case "DELETE":
				return LogEntryType.DELETE;
			case "PUBLISH":
				return LogEntryType.PUBLISH;
			case "LOG_UPLOAD":
				return LogEntryType.LOG_UPLOAD;
			case "IMAGE_UPLOAD":
				return LogEntryType.IMAGE_UPLOAD;
			case "ATTACHMENT_UPLOAD":
				return LogEntryType.ATTACHMENT_UPLOAD;
			case "IMAGE_PUBLISH":
				return LogEntryType.IMAGE_PUBLISH;
			case "ATTACHMENT_PUBLISH":
				return LogEntryType.ATTACHMENT_PUBLISH;
			case "IMAGE_UNPUBLISH":
				return LogEntryType.IMAGE_UNPUBLISH;
			case "ATTACHMENT_UNPUBLISH":
				return LogEntryType.ATTACHMENT_UNPUBLISH;
			case "IMAGE_DELETE":
				return LogEntryType.IMAGE_DELETE;
			case "ATTACHMENT_DELETE":
				return LogEntryType.ATTACHMENT_DELETE;
			case "REVERT":
				return LogEntryType.REVERT;
		}
		return null;
	}
	
	static [Symbol.iterator]() {
		return [LogEntryType.SITE_PROPOSED, LogEntryType.ADD, LogEntryType.UPDATE, LogEntryType.DELETE, LogEntryType.PUBLISH, LogEntryType.LOG_UPLOAD, LogEntryType.IMAGE_UPLOAD, LogEntryType.ATTACHMENT_UPLOAD, LogEntryType.IMAGE_PUBLISH, LogEntryType.ATTACHMENT_PUBLISH, LogEntryType.IMAGE_UNPUBLISH, LogEntryType.ATTACHMENT_UNPUBLISH, LogEntryType.IMAGE_DELETE, LogEntryType.ATTACHMENT_DELETE, LogEntryType.REVERT][Symbol.iterator]();
	}
}
class SiteLogStatus {
	
	static FORMER = new SiteLogStatus(1, "FORMER", "Former", "slm-status-former", "#3D4543", "Site is no longer maintained and logs are not published.");
	static PROPOSED = new SiteLogStatus(2, "PROPOSED", "Proposed", "slm-status-proposed", "#913D88", "This is a new Site that has never been published.");
	static UPDATED = new SiteLogStatus(3, "UPDATED", "Updated", "slm-status-updated", "#0079AD", "Site log or section has unpublished updates.");
	static PUBLISHED = new SiteLogStatus(4, "PUBLISHED", "Published", "slm-status-published", "#0D820D", "Site log or section is published with no unpublished changes.");
	static EMPTY = new SiteLogStatus(5, "EMPTY", "Empty", "slm-status-empty", "#D3D3D3", "Site log section is empty or deleted.");
	static SUSPENDED = new SiteLogStatus(6, "SUSPENDED", "Suspended", "slm-status-suspended", "#E0041A", "Site has been temporarily suspended and does not appear in public data.");
	
	constructor (value, name, label, css, color, help) {
		this.value = value;
		this.name = name;
		this.label = label;
		this.css = css;
		this.color = color;
		this.help = help;
	}
	
	toString() {
		return this.label;
	}
	
	static get(value) {
		switch(value) {
			case 1:
				return SiteLogStatus.FORMER;
			case 2:
				return SiteLogStatus.PROPOSED;
			case 3:
				return SiteLogStatus.UPDATED;
			case 4:
				return SiteLogStatus.PUBLISHED;
			case 5:
				return SiteLogStatus.EMPTY;
			case 6:
				return SiteLogStatus.SUSPENDED;
		}
		switch(value) {
			case "FORMER":
				return SiteLogStatus.FORMER;
			case "PROPOSED":
				return SiteLogStatus.PROPOSED;
			case "UPDATED":
				return SiteLogStatus.UPDATED;
			case "PUBLISHED":
				return SiteLogStatus.PUBLISHED;
			case "EMPTY":
				return SiteLogStatus.EMPTY;
			case "SUSPENDED":
				return SiteLogStatus.SUSPENDED;
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
	
	toString() {
		return this.name;
	}
	
	static get(value) {
		switch(value) {
			case 1:
				return AlertLevel.NOTICE;
			case 2:
				return AlertLevel.WARNING;
			case 3:
				return AlertLevel.ERROR;
		}
		switch(value) {
			case "NOTICE":
				return AlertLevel.NOTICE;
			case "WARNING":
				return AlertLevel.WARNING;
			case "ERROR":
				return AlertLevel.ERROR;
		}
		switch(value) {
			case "NOTICE":
				return AlertLevel.NOTICE;
			case "WARNING":
				return AlertLevel.WARNING;
			case "ERROR":
				return AlertLevel.ERROR;
		}
		return null;
	}
	
	static [Symbol.iterator]() {
		return [AlertLevel.NOTICE, AlertLevel.WARNING, AlertLevel.ERROR][Symbol.iterator]();
	}
}
class SiteFileUploadStatus {
	
	static UNPUBLISHED = new SiteFileUploadStatus(1, "UNPUBLISHED", "Unpublished File", "slm-upload-unpublished file", "#0079AD", "The file is pending moderation before it will be made public.");
	static PUBLISHED = new SiteFileUploadStatus(2, "PUBLISHED", "Published File", "slm-upload-published file", "#0D820D", "The file is published and is publicly available as an attachment to the site.");
	static INVALID = new SiteFileUploadStatus(3, "INVALID", "Invalid Site Log", "slm-upload-invalid site log", "#8b0000", "The file did not pass validation.");
	static WARNINGS = new SiteFileUploadStatus(4, "WARNINGS", "Warnings Site Log", "slm-upload-warnings site log", "#E3AA00", "The file is valid but has some warnings.");
	static VALID = new SiteFileUploadStatus(5, "VALID", "Valid Site Log", "slm-upload-valid site log", "#0D820D", "The file is valid.");
	
	constructor (value, name, label, css, color, help) {
		this.value = value;
		this.name = name;
		this.label = label;
		this.css = css;
		this.color = color;
		this.help = help;
	}
	
	toString() {
		return this.label;
	}
	
	static get(value) {
		switch(value) {
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
		switch(value) {
			case "UNPUBLISHED":
				return SiteFileUploadStatus.UNPUBLISHED;
			case "PUBLISHED":
				return SiteFileUploadStatus.PUBLISHED;
			case "INVALID":
				return SiteFileUploadStatus.INVALID;
			case "WARNINGS":
				return SiteFileUploadStatus.WARNINGS;
			case "VALID":
				return SiteFileUploadStatus.VALID;
		}
		return null;
	}
	
	static [Symbol.iterator]() {
		return [SiteFileUploadStatus.UNPUBLISHED, SiteFileUploadStatus.PUBLISHED, SiteFileUploadStatus.INVALID, SiteFileUploadStatus.WARNINGS, SiteFileUploadStatus.VALID][Symbol.iterator]();
	}
}
class SiteLogFormat {
	
	static LEGACY = new SiteLogFormat(1, "LEGACY", "Legacy (ASCII)", "text/plain", "bi bi-file-text", "log", ["text", "txt"]);
	static GEODESY_ML = new SiteLogFormat(2, "GEODESY_ML", "GeodesyML", "application/xml", "bi bi-filetype-xml", "xml", ["xml"]);
	static JSON = new SiteLogFormat(3, "JSON", "JSON", "application/json", "bi bi-filetype-json", "json", ["json", "js"]);
	
	constructor (value, name, label, mimetype, icon, ext, alts) {
		this.value = value;
		this.name = name;
		this.label = label;
		this.mimetype = mimetype;
		this.icon = icon;
		this.ext = ext;
		this.alts = alts;
	}
	
	toString() {
		return this.label;
	}
	
	static get(value) {
		switch(value) {
			case 1:
				return SiteLogFormat.LEGACY;
			case 2:
				return SiteLogFormat.GEODESY_ML;
			case 3:
				return SiteLogFormat.JSON;
		}
		switch(value) {
			case "LEGACY":
				return SiteLogFormat.LEGACY;
			case "GEODESY_ML":
				return SiteLogFormat.GEODESY_ML;
			case "JSON":
				return SiteLogFormat.JSON;
		}
		switch(value) {
			case "text/plain":
				return SiteLogFormat.LEGACY;
			case "application/xml":
				return SiteLogFormat.GEODESY_ML;
			case "application/json":
				return SiteLogFormat.JSON;
		}
		switch(value) {
			case "log":
				return SiteLogFormat.LEGACY;
			case "xml":
				return SiteLogFormat.GEODESY_ML;
			case "json":
				return SiteLogFormat.JSON;
		}
		return null;
	}
	
	static [Symbol.iterator]() {
		return [SiteLogFormat.LEGACY, SiteLogFormat.GEODESY_ML, SiteLogFormat.JSON][Symbol.iterator]();
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
	
	toString() {
		return this.label;
	}
	
	static get(value) {
		switch(value) {
			case 1:
				return SLMFileType.SITE_LOG;
			case 2:
				return SLMFileType.SITE_IMAGE;
			case 3:
				return SLMFileType.ATTACHMENT;
		}
		switch(value) {
			case "SITE_LOG":
				return SLMFileType.SITE_LOG;
			case "SITE_IMAGE":
				return SLMFileType.SITE_IMAGE;
			case "ATTACHMENT":
				return SLMFileType.ATTACHMENT;
		}
		switch(value) {
			case "log":
				return SLMFileType.SITE_LOG;
			case "image":
				return SLMFileType.SITE_IMAGE;
			case "attachment":
				return SLMFileType.ATTACHMENT;
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
