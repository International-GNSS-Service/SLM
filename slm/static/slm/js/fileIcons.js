if (typeof slm === 'undefined' || slm == null) { var slm = {}; }


slm.iconMap = {
    'zip': 'bi bi-file-zip',
    'x-tar': 'bi bi-file-zip',
    'plain': 'bi bi-filetype-txt',
    'jpeg': 'bi bi-filetype-jpg',
    'svg+xml': 'bi bi-filetype-svg',
    'xml': 'bi bi-filetype-xml',
    'json': 'bi bi-filetype-json',
    'png': 'bi bi-filetype-png',
    'tiff': 'bi bi-filetype-tiff',
    'pdf': 'bi bi-filetype-pdf',
    'gif': 'bi bi-filetype-gif',
    'csv': 'bi bi-filetype-csv',
    'bmp': 'bi bi-filetype-bmp',
    'vnd.openxmlformats-officedocument.wordprocessingml.document': 'bi bi-filetype-doc',
    'msword': 'bi bi-filetype-doc'
};

slm.fileIcon = function(mimetype) {
    if (mimetype) {
        let subtype = mimetype.substring(mimetype.indexOf('/') + 1);
        if (slm.iconMap.hasOwnProperty(subtype)) {
            return slm.iconMap[subtype];
        }
    }
    return "bi bi-file-earmark";
};
