if (typeof slm === 'undefined' || slm == null) { var slm = {}; }

// TODO generate w/renderstatic

class LogEntryType {
  static NEW_SITE = new LogEntryType(1,'New Site');
  static ADD = new LogEntryType(2,'Add');
  static UPDATE = new LogEntryType(3,'Update');
  static DELETE = new LogEntryType(4,'Delete');
  static PUBLISH = new LogEntryType(5,'Publish');

  constructor(val, label) {
      this.val = val;
      this.label = label;
      this.css = `slm-log-${this.label.toLowerCase()}`;
  }
  toString() {
    return `LogEntryType.${this.label}`;
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

  // todo DRY the colors (i.e. pull from settings)
  static DORMANT = new SiteLogStatus(0,'Dormant', '#3D4543');
  static PENDING = new SiteLogStatus(1,'Pending', '#913D88');
  static UPDATED = new SiteLogStatus(2,'Updated', '#BF8C0D');
  static PUBLISHED = new SiteLogStatus(3,'Published', '#008000');

  constructor(val, label, color) {
      this.val = val;
      this.label = label;
      this.css = `slm-status-${this.label.toLowerCase()}`;
      this.color = color;
  }
  toString() {
    return `SiteLogStatus.${this.label}`;
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
      }
      return SiteLogStatus.DORMANT; // todo remove
  }
}

class AlertLevel {

  static INFO = new AlertLevel(0,'INFO');
  static WARNING = new AlertLevel(1,'WARNING');
  static ERROR = new AlertLevel(2,'ERROR');

  constructor(val, label, color) {
      this.val = val;
      this.label = label;
      this.bootstrap = `${label.toLowerCase()}`;
      if (this.val === 1){
          this.bootstrap = 'warning';
      } else if (this.val === 2) {
          this.bootstrap = 'danger';
      }
  }
  toString() {
    return `AlertLevel.${this.label}`;
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
