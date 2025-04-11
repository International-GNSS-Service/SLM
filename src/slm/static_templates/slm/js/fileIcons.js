if (typeof slm === 'undefined' || slm == null) { var slm = {}; }


slm.iconMap = {{% for subtype, icon in ICON_MAP.items %}
    '{{ subtype }}': '{{ icon }}'{% if not forloop.last %},{% endif %}{% endfor %}
};

slm.fileIcon = function(mimetype) {
    if (mimetype) {
        let subtype = mimetype.substring(mimetype.indexOf('/') + 1);
        if (slm.iconMap.hasOwnProperty(subtype)) {
            return slm.iconMap[subtype];
        }
    }
    return "{{ DEFAULT_ICON }}";
};
