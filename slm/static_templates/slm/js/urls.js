if (typeof slm === 'undefined' || slm == null) { var slm = {}; }

{% urls_to_js exclude=exclude visitor="render_static.ClassURLWriter" %}

slm.urls = new URLResolver();
