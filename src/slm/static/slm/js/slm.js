if (typeof slm === 'undefined' || slm === null) { var slm = {}; }

$(document).ready(function() {
    $(".collapse .nav-link").click(function () {
        $(".collapse .nav-link").removeClass("active");
        $(this).addClass("active");
    });

    $('[data-bs-toggle="tooltip"]').tooltip();
    $('[data-bs-toggle="popover"]').popover();

    $('.slm-form').each(function() {
        slm.initForm($(this));
    });
});

/*slm.popover = new bootstrap.Popover(
    document.querySelector('.popover-dismiss'),
    {
        trigger: 'focus',
        container: 'body'
    }
);*/

class ErrorBadgeUpdater {

    constructor(form) {
        this.form = form;
        this.delta = null;
    }
    
    visit(node) {
        if (this.delta === null) {
            this.delta = Object.keys(this.form.data('slmErrorFlags')).length -
                (node.data('slmFlags') || 0);
        }
        let badge = node.find('span.slm-error-badge');
        let newNum = (node.data('slmFlags') || 0) + this.delta;
        newNum = newNum < 0 ? 0 : newNum;
        node.data('slmFlags', newNum);
        if (newNum <= 0) {
            badge.hide();
            badge.html(0);
        } else {
            badge.show();
            badge.html(newNum);
        }
    }
}

class StatusUpdater {

    constructor(form, status) {
        this.form = form;
        if (!status instanceof SiteLogStatus) {
            this.status = slm.SiteLogStatus.get(status);
        } else {
            this.status = status;
        }
    }

    visit(node) {
        /* update navigation button status classes and data */
        let currentStatus = slm.SiteLogStatus.get(
            node.data('slmStatus')
        );
        if (currentStatus !== null) {
            this.status = currentStatus.set(this.status);
            node.removeClass(currentStatus.css);
        }
        node.addClass(this.status.css);
        node.data('slmStatus', this.status.value);
        slm.getNavSiblings(node).each(function(idx, sibling) {
            this.status = this.status.merge(
                slm.SiteLogStatus.get(
                    $(sibling).data('slmStatus')
                )
            )
        }.bind(this));
    }
}

slm.isModerator = !slm.hasOwnProperty('isModerator') ? false : slm.isModerator;
slm.canPublish = !slm.hasOwnProperty('canPublish') ? false : slm.canPublish;

slm.handlePostSuccess = function(form, response, status, jqXHR) {
    form.find('button').blur();
    const data = response && response.hasOwnProperty('results') ? response.results : response;
    if (jqXHR.status === 204) {
        form.data('slmErrorFlags', {});
        slm.visitEditNavTree(form, new ErrorBadgeUpdater(form));
        slm.visitEditNavTree(
            form,
            new StatusUpdater(
                form,
                SiteLogStatus.EMPTY
            )
        );
        form.closest('.accordion-item').remove();
        return;
    }
    if (jqXHR.status === 205) {
        return window.location.reload();
    }
    form.data('slmId', data.id);
    form.find('input[name="id"]').val(data.id);
    if (data.hasOwnProperty('subsection')) {
        form.find('input[name="subsection"]').val(data.subsection);
    }
    if (data.is_deleted) {
        form.addClass('slm-section-deleted');
        form.closest('.accordion-item').find(
            'button.accordion-button'
        ).addClass('slm-section-deleted').removeClass(
            'slm-status-published'
        ).addClass('slm-status-updated');
        form.find('.alert.slm-form-deleted').show();
        form.find('.form-control:visible').attr('disabled', '');
        form.find('input.form-check-input:visible').attr('disabled', '');
        form.find('.slm-flag').hide();
        form.find('div[contenteditable]').removeAttr('contenteditable');
    } else {
        if (slm.isModerator) {
            form.find('.slm-flag').show();
        } else {
            form.find('.slm-flag').hide();
        }
        form.removeClass('slm-section-deleted');
        form.closest('.accordion-item').find(
            'button.accordion-button'
        ).removeClass('slm-section-deleted');
        form.find('.alert.slm-form-deleted').hide();
        form.find('.slm-flag').show();
        form.find('div[contenteditable]').attr('contenteditable', true);
        
        // TODO Form class setters/getters still not completely working for all forms
        // const filterForm = new slm.Form(form);
        // filterForm.data = data;
    }

    if (data.hasOwnProperty('_diff') && Object.keys(data._diff).length) {
        if (!data.is_deleted) {
            form.find('.alert.slm-form-unpublished').show();
        }
        for (const [field, diff] of Object.entries(data._diff)) {
            const formField = form.find(`#id_${field}-${form.attr('id').replace('site-', '')}`);
            formField.addClass('is-invalid');
            if (data.hasOwnProperty('_flags') && !data._flags.hasOwnProperty(field)) {
                formField.addClass('slm-form-unpublished');
            }
            formField.after(
                `<div class="invalid-feedback slm-form-unpublished">The published value is ${diff.pub}</div>`
            );
        }
    }
    let headingButton = form.closest('.accordion-item').find('button.accordion-button');
    headingButton.find('.slm-heading').html(data.heading);
    headingButton.find('.slm-effective').html(data.effective);
    if (data.hasOwnProperty('_flags')) {
        form.data('slmErrorFlags', data._flags);
        slm.setFormFlagUI(form);
    }
    if (
        (data.hasOwnProperty('published') && !data.published) ||
        (data.hasOwnProperty('is_deleted') && data.is_deleted)
    ) {
        if (data.can_publish) {
            form.find('button[name="publish"]').show();
        }
        if (form.data('hasPublished')) {
            form.find('button[name="revert"]').show();
        }
    }
    if (data.hasOwnProperty('is_deleted') && data.is_deleted) {
        form.find('button[name="delete"]').hide();
        form.find('button[name="save"]').hide();
    } else if (data.hasOwnProperty('is_deleted')) {
        form.find('button[name="delete"]').show();
    }

    slm.visitEditNavTree(form, new ErrorBadgeUpdater(form));
    slm.visitEditNavTree(
        form,
        new StatusUpdater(
            form,
            data.published ? SiteLogStatus.PUBLISHED : SiteLogStatus.UPDATED
        )
    );
}

slm.handlePostErrors = function(form, jqXHR, status, text) {
    if (jqXHR.hasOwnProperty('responseJSON')) {
        const data = jqXHR.responseJSON;
        if (Array.isArray(data)) {
            for (const error of data) {
                form.prepend(`<div class="alert alert-danger slm-form-fail"><strong>${error}</strong></div>`);
            }
        } else {
            for (const [key, value] of Object.entries(data)) {
                let errorElem = form.find(`#id_${key}-${form.attr('id').replace('site-', '')}`);
                errorElem.addClass('is-invalid');
                errorElem.after(`<div class="invalid-feedback">${value}</div>`);
            }
        }
    } else if (jqXHR.hasOwnProperty('responseText')) {
        form.prepend(`<div class="alert alert-danger slm-form-fail"><strong>${jqXHR.responseText}</strong></div>`);
    } else {
        alert('Unknown error!');
    }
}

slm.resetFormErrorsAndWarnings = function(form) {
    form.find('.is-invalid.slm-form-unpublished').removeClass('.slm-form-unpublished');
    form.find('.is-invalid').removeClass('is-invalid');
    form.find('.invalid-feedback').remove();
    form.find('.slm-form-fail').remove();
    form.find('.alert.slm-form-unpublished').hide();
    form.find('.alert.slm-form-error').hide();
    //form.find('button[name="publish"]').hide();
}

slm.initForm = function(form_id, initial=null, transform= function(data){ return data; }) {
    const form = typeof form_id === 'string' || form_id instanceof String ? $(form_id) : form_id;
    const form_api = form.data('slmApi');
    const form_url = form.data('slmUrl');
    if (form.data('slmFlags')) {
        form.data(
            'slmErrorFlags',
            JSON.parse(document.getElementById(form.data('slmFlags')).textContent)
        );
    } else {
        form.data('slmErrorFlags', {});
    }
    if (initial) {
        slm.setFormFields(form, initial);
    }
    const handleSubmit = function(action, btn) {
        slm.resetFormErrorsAndWarnings(form);
        let data = slm.formToObject(form);
        const csrf = data.csrfmiddlewaretoken;
        delete data.csrfmiddlewaretoken;
        let request = null;
        const dataId = data.id || form.data('slmId');
        let finished = function() {};
        let formBtn = form.closest('.accordion-item');
        if (action === 'delete') {
            formBtn.prevAll().find('span.section-number').each(
                function(){
                    $(this).text(slm.incrSectionNumber($(this).text(), -1));
                }
            );
            formBtn.find('span.section-number').remove();
            if (!dataId) {
                formBtn.remove();
                return;
            }
            if (btn) {
                finished = slm.processing(btn);
            }
            request = $.ajax({
                url: form_url ? form_url : slm.urls.reverse(`${form_api}-detail`, {kwargs: {'pk': dataId}}),
                method: 'DELETE',
                headers: {'X-CSRFToken': csrf}
            })
        } else if (action === 'publish' || action === 'revert') {
            let toPost = transform(data);
            toPost[action] = true;
            let options = {};
            let endpoint = `${form_api}-list`;
            let method = 'POST';
            if (dataId) {
                endpoint = `${form_api}-detail`;
                options['pk'] = dataId;
                method = 'PATCH';
            }
            if (btn) {
                let btnFinished = slm.processing(btn);
                finished = function() {
                    btn.hide();
                    btnFinished();
                }
            }
            request = $.ajax({
                url: form_url ? form_url : slm.urls.reverse(endpoint, {kwargs: options}),
                method: method,
                headers: {'X-CSRFToken': csrf},
                data: toPost
            });
        } else {
            if (btn) {
                finished = slm.processing(btn);
            }
            request = $.ajax({
                url: form_url ? form_url : slm.urls.reverse(`${form_api}-list`),
                method: form.attr('data-slm-method') ? form.attr('data-slm-method') : 'POST',
                headers: {'X-CSRFToken': csrf}, // todo still necessary?
                data: JSON.stringify(transform(data)),
                contentType: 'application/json; charset=utf-8',
                dataType: 'json',
            });
        }

        request.done(
            function(data, status, jqXHR) {
                if (action === 'revert') {
                    window.location.reload();
                }
                finished();
                if (data) {
                    $.ajax({
                        url: slm.urls.reverse(
                            'slm_edit_api:stations-detail',
                            {kwargs: {pk: data.site}}
                        )
                    }).done(function (site, status, jqXHR) {
                        slm.updateAlertBell(site);
                    });
                }
                if (action === 'publish') {
                    form.data('hasPublished', true);
                }
                slm.handlePostSuccess(form, data, status, jqXHR);
            }
        ).fail(
            function(jqXHR, status, text) {
                finished();
                slm.handlePostErrors(form, jqXHR, status, text);
            }
        );
    };
    form.on('click', 'button[name="save"]', function() { handleSubmit('save', $(this)); });
    form.on('click', 'button[name="delete"]', function() { handleSubmit('delete', $(this)); });
    form.on('click', 'button[name="publish"]', function() { handleSubmit('publish', $(this)); });
    form.on('click', 'button[name="revert"]', function() { handleSubmit('revert', $(this)); });
    form.submit(function(event){ event.preventDefault(); handleSubmit(false);});

    form.on('click', '.slm-flag-error', function() {
        let field = $(this).closest('.slm-form-fieldset');
        let inpt = field.find('.slm-flag-input');
        let fieldInpt = field.find(`.slm-form-field[name="${$(field).data('slmField')}"]`);
        if (inpt.is(":visible")) {
            $(this).html('<i class="bi bi-flag"></i><i class="bi bi-flag-fill"></i>');
            inpt.val('');
            if (slm.isUnpublished(field)) {
                fieldInpt.addClass('is-invalid');
                fieldInpt.addClass('slm-form-unpublished');
            } else {
                fieldInpt.removeClass('is-invalid');
                fieldInpt.removeClass('slm-form-unpublished');
            }
            inpt.hide();
            slm.flagsUpdated(form);
        } else {
            $(this).html('<i class="bi bi-x-circle"></i><i class="bi bi-x-circle-fill"></i>');
            fieldInpt.addClass('is-invalid');
            fieldInpt.addClass('is-invalid');
            fieldInpt.removeClass('slm-form-unpublished');
            inpt.show();
            inpt.focus();
        }
    });
    form.find('.slm-flag-input').keypress(function(event) {
        // de-focus on enter triggering update
        if ((event.keyCode ? event.keyCode : event.which) === 13 ) {
            $(this).blur();
        }
    });
    form.on('blur', '.slm-flag-input', function() {
        if (!$(this).val()) {
            $(this).closest('.slm-form-field').find('.slm-flag-error').trigger('click');
        } else {
            slm.flagsUpdated(form);
        }
    });
    slm.time24Init(form.find('fieldset.time-24hr'));
}

slm.extractFlags = function(form) {
    const flags = {};
    form.find('input.slm-flag-input').each(function() {
        if ($(this).val()) {
            flags[$(this).attr('data-slm-field')] = $(this).val();
        }
    });
    return flags;
}

slm.setFormFlagUI = function(form) {
    form.find('fieldset:visible').each(
        function() {
            let fieldInpt = $(this).find(`.slm-form-field[name="${$(this).data('slmField')}"]`);
            if (form.data('slmErrorFlags').hasOwnProperty($(this).data('slmField'))) {
                let flag = form.data('slmErrorFlags')[$(this).data('slmField')];
                $(this).find('.slm-flag-error').html(
                    '<i class="bi bi-x-circle"></i><i class="bi bi-x-circle-fill"></i>'
                );
                let inpt = $(this).find('input.slm-flag-input');
                inpt.val(flag);
                inpt.show();
                let err = $(this).find('div.slm-form-error');
                err.html(flag);
                err.show();
                fieldInpt.addClass('is-invalid');
                fieldInpt.removeClass('slm-form-unpublished');
            } else {
                $(this).find('.slm-flag-error').html(
                    '<i class="bi bi-flag"></i><i class="bi bi-flag-fill"></i>'
                );
                let inpt = $(this).find('input.slm-flag-input');
                inpt.val('');
                inpt.hide();
                let err = $(this).find('div.slm-form-error');
                err.html('');
                err.hide();
                if (slm.isUnpublished($(this))) {
                    fieldInpt.addClass('is-invalid');
                    fieldInpt.addClass('slm-form-unpublished');
                } else {
                    fieldInpt.removeClass('is-invalid');
                    fieldInpt.removeClass('slm-form-unpublished');
                }
            }
        }
    );
    slm.visitEditNavTree(form, new ErrorBadgeUpdater(form));
}

slm.visitEditNavTree = function(form, visitor) {
    /* visit navigation ancestor buttons from the top up */
    let node = $(form).closest('.accordion-item').find('button.slm-subsection');
    if (!node.length) {
        node = $(`button[data-slm-section="${form.data('slmSection')}"]`);
    }
    while (node.data('slmParent')) {
        visitor.visit(node);
        node = $(`button#${node.data('slmParent')}`);
    }
    visitor.visit(node);
}

slm.getNavSiblings = function(editNavButton) {
    return $(`button[data-slm-parent="${editNavButton.data('slmParent')}"`);
}

slm.isUnpublished = function(fieldset) {
    return fieldset.find('div.slm-form-unpublished').text().length > 0;
}

slm.flagsUpdated = function(form) {
    let doUpdate = function() {
        form.data('slmErrorFlags', newFlags);
        const data = Object.fromEntries(new FormData(form.get(0)).entries());
        const form_api = form.attr('data-slm-api');
        const form_url = form.attr('data-slm-url');
        const csrf = data.csrfmiddlewaretoken;
        delete data.csrfmiddlewaretoken;
        $.ajax({
            url: form_url ? form_url : slm.urls.reverse(`${form_api}-detail`, {kwargs: {'pk': data.id}}),
            method: 'PATCH',
            headers: {'X-CSRFToken': csrf},
            data: JSON.stringify({'_flags': form.data('slmErrorFlags')}),
            contentType: "application/json"
        }).fail(
            function( jqXHR, status, errorTxt ) {
                console.log(jqXHR);
                alert(`Error setting flags: ${errorTxt}`);
            }
        ).done(function() { slm.setFormFlagUI(form); });
    }
    const newFlags = slm.extractFlags(form);
    if (
        Object.keys(newFlags).length !== Object.keys(form.data('slmErrorFlags')).length
    ) {
        doUpdate();
    } else {
        for (const [flag, val] of Object.entries(newFlags)) {
            if (!form.data('slmErrorFlags').hasOwnProperty(flag) || form.data('slmErrorFlags')[flag] !== val) {
                doUpdate();
            }
        }
    }
}

slm.flipIcons = function(container) {
    container.append(container.children('i').get().reverse());
}

slm.getName = function(user) {
    if (user) {
        if (user.first_name || user.last_name) {
            return `${user.first_name} ${user.last_name}`;
        }
        return `${user.email}`;
    }
    return '';
}

slm.mailToUser = function(user) {
    if (user) {
        return `<a href="mailto:${user.email}">${slm.getName(user)}</a>`;
    }
    return '';
}

slm.initInfiniteScroll = function(div, scrollDiv, loader, api, kwargs, query, draw, cache=false) {
    div = $(div);
    scrollDiv = scrollDiv === null ? $(window) : scrollDiv;
    const atBottom = $.isWindow(scrollDiv.get(0)) ? slm.windowAtBottom : slm.scrollAtBottom;
    const position = div.find('> div').last();
    if (loader === null) {
        loader = position;
    }
    const drawPage = function(data) {
        loader.hide();
        if (data.next) {
            scrollDiv.scroll(function() {
                if (atBottom(scrollDiv.get(0))) {
                    fetchPage();
                }
            });
        }
        draw(
            position,
            data.hasOwnProperty('results') ?
                data.results : data.hasOwnProperty('data') ?
                data.data : data,
            data.hasOwnProperty('recordsFiltered') ? data.recordsFiltered : null,
            data.hasOwnProperty('recordsTotal') ? data.recordsTotal : null
        );
        div.data('slmPage', div.data('slmPage') + query.length);
    };
    const fetchPage = function() {
        loader.show();
        scrollDiv.off( 'scroll' );
        query = Object.assign(
            query,
            Object.assign(
                div.data('slmQuery') || {},
                {
                    start: div.data('slmPage'),
                    length: div.data('slmPageSize')
                }
            )
        );
        const queryUrl = slm.urls.reverse(api, {kwargs: kwargs, query: query});
        const cached = sessionStorage.getItem(queryUrl);
        if (cached) {
            drawPage(JSON.parse(cached));
        } else {
            $.ajax({url: queryUrl}).done(
                (data) => {
                    if (cache) {
                        sessionStorage.setItem(queryUrl, JSON.stringify(data));
                    }
                    drawPage(data);
                }
            ).fail((jqXHR) => {
                console.log(jqXHR);
            });
        }
    }
    fetchPage(); 
}

slm.scrollAtBottom = function(div) {
    return div.offsetHeight + div.scrollTop >= div.scrollHeight;
}

slm.windowAtBottom = function() {
    return (window.innerHeight + window.scrollY) >= document.body.scrollHeight
}

slm.initStationList = function(listId, station, searchId, stationTmpl) {
    const stationList = $(listId);
    const searchInput = $(searchId);
    if (station) {
        stationList.scrollTop(
            document.getElementById(`select-${ station }`).offsetTop - stationList.before().position().top
        );
    }
    slm.stationListOrig = null;
    let keyupTimeoutID = 0;
    searchInput.on('input', function() {
        clearTimeout(keyupTimeoutID);
        keyupTimeoutID = setTimeout(function() {
            if (slm.stationListOrig === null) {
                slm.stationListOrig = $('#station-list > button').detach();
            }
            if (searchInput.val()) {
                $.ajax({
                    url: slm.urls.reverse('slm_edit_api:stations-list'),
                    method: 'GET',
                    data: {
                        name__icontains: searchInput.val()
                    }
                }).done(
                    function (response) {
                        const stations = response.hasOwnProperty('results') ? response.results : response;
                        stationList.empty();
                        for (const station of stations) {
                            stationList.append(stationTmpl(station.name));
                        }
                        // TODO FIX THIS disgusting kludge to fix some css problems - nav pills are stretched,
                        //  as if in justify-content stretch mode even though they arent, so we just add some hidden
                        //  elements to make the spacing look right
                        let neededFiller = 100 - stations.length;
                        if (neededFiller > 0) {
                            for (var i = 0; i < neededFiller; i++) {
                                stationList.append('<button style="visibility: hidden">FILLER</button>');
                            }
                        }
                    }
                )
            } else {
                stationList.empty();
                stationList.append(slm.stationListOrig);
            }
        }, 500);
    });
}


slm.showDiff = function(head, ancestor, display, mode='char') {
    let dmp = new diff_match_patch();
    dmp.Diff_EditCost = 4;
    let lineArray = null;
    if (mode !== 'char') {
        let a = null;
        if (mode === 'line') {
            a = dmp.diff_linesToChars_(ancestor, head);
        } else {
            a = dmp.diff_linesToWords_(ancestor, head);
        }
        ancestor = a.chars1;
        head = a.chars2;
        lineArray = a.lineArray;
    }
    let diffs = dmp.diff_main(ancestor, head, mode === 'char');
    dmp.diff_cleanupSemantic(diffs);
    if (mode !== 'char') {
        dmp.diff_charsToLines_(diffs, lineArray);
    }
    //dmp.diff_cleanupEfficiency(0);
    //display.html(dmp.diff_prettyHtml(diffs));
    display.html(`<div class="slm-diff-header"></div><span class="slm-review-lineno"> </span><span class="slm-review-line"></span><br/>${slm.prettyHtml(diffs)}<div class="slm-diff-footer"></div>`);
}

slm.setDateTimeWidget = function(widget, datetime, attr=null, length=16) {
    let val = null;
    if (datetime) {
        datetime = new Date(datetime.getTime());
        datetime.setMinutes(datetime.getMinutes() - datetime.getTimezoneOffset());
        val = datetime.toISOString().slice(0, length);
    }
    if (attr !== null) {
        widget.attr(attr, val);
    } else {
        widget.val(val);
    }
}

slm.prettyHtml = function(diffs) {
    let html = [];
    let pattern_amp = /&/g;
    let pattern_lt = /</g;
    let pattern_gt = />/g;
    let pattern_crlf = /\r/g;
    let lineno = 0;
    for (let x = 0; x < diffs.length; x++) {
      let start = lineno;
      let op = diffs[x][0];    // Operation (insert, delete, equal)
      let data = diffs[x][1];  // Text of change.
      let text = data.replace(pattern_amp, '&amp;').replace(pattern_lt, '&lt;').replace(pattern_gt, '&gt;').replace(pattern_crlf, '');
      let lines = [];
      for (const line of text.slice(0,text.length-1).split('\n')) {
          lineno++;
          lines.push(`<span class="slm-review-lineno">${lineno}</span><span class="slm-review-line">${line}</span>`);
      }
      text = lines.join('\n');
      switch (op) {
        case DIFF_INSERT:
          html[x] = `<ins style="background:#e6ffe6;">${text}</ins><br/>`;
          break;
        case DIFF_DELETE:
          html[x] = `<del style="background:#ffe6e6;">${text}</del><br/>`;
          lineno = start;
          break;
        case DIFF_EQUAL:
          html[x] = `<span class="slm-diff-equal">${text}</span><br/>`;
          break;
      }
    }
    return html.join('');
};


slm.addColumnFiltering = function( table) {
    /**
     * Add column filtering to our table's sub header row. The filtering selections are redone each time new data
     * is fetched from ajax so the available values can be redone based on the other active filters. See filterableCols
     * on the api data.
     */
    const value_map = { };
    let api = table.api;
    let id = table.id;

    // do this each time we receive new data via ajax
    table.api.on( 'xhr', function ( ) {
        let data = api.ajax.json( ) ;
        // add filtering drop downs - the strategy is to copy the header row and walk through the columns adding a drop
        // down wherever a column is found in the filterableCols attribute on the data received from the server
        let hdr_row = $( '#' + id + ' thead tr.filter_row' );
        hdr_row.remove( );
        if ( data.filterableCols ) {
            $( '#' + id + ' thead tr' ).clone( true ).appendTo( '#' + id + ' thead' ).addClass( 'filter_row' );
            $( '#' + id + ' thead tr:eq(1) th' ).each( function ( i ) {
                let centered = $( this ).hasClass( 'dt-center' );
                let col_name = $( this ).html( );
                $( this ).html( '' );
                $( this ).removeAttr( 'aria-controls' ).removeAttr( 'tabindex' ).removeAttr( 'class' );
                $( this ).off( 'click' );
                if ( col_name in data.filterableCols ) {
                    if ( centered ) {
                        $( this ).addClass( 'dt-center' );
                    }
                    $( this ).addClass( 'filter-column' );
                    let idx = data.filterableCols[col_name][0];
                    let selected = '';
                    if ( api.ajax.params( ).hasOwnProperty( idx ) ) {
                        selected = api.ajax.params( )[idx];
                    }
                    var title = $( this ).text( );
                    let html = '<select id=' + id + '__filter_col_' +  idx + ' name=' +  idx + ' placeholder="Filter ' + title + '">';
                    html += '<option ' + (selected === '' ? 'selected' : '') + ' value></option>';
                    if ( selected === 'false' ) {
                        selected = false;
                    }
                    else if ( selected === 'true' ) {
                        selected = true;
                    }
                    else if ( selected === 'null' ) {
                        selected = null;
                    }
                    data.filterableCols[col_name][1].forEach(function(value) {
                        let strValue = value;
                        if ( value !== null && Number.isFinite(value) ) strValue = value.toString( );
                        html += '<option ' + ( selected === strValue ? 'selected' : '' ) + ' value="' + value + '">' + (col_name in value_map ? value_map[col_name](value) : value) + '</option>'
                    });
                    html += '</select>'

                    $( this ).html(html);
                    $( 'select', this ).on( 'change', function ( ) {
                        api.ajax.reload( );
                    });
                }
            });

            hdr_row.on( 'click', 'thead th', function ( e ) {
                // make it so we dont trigger a reorder when we select dropdown
                e.preventDefault( );
            });
        }
    });
};


slm.dataTablesAdaptor = function( data, select=null ) {
    /**
     * Massage our datatables ajax query parameters into names understood by the server. See The base view class for
     * any datatables enabled web api view.
     */
    select['draw'] = data.draw;
    select['length'] = data.length;
    select['order[0][column]'] = data.order[0]['column'];
    select['order[0][dir]'] = data.order[0]['dir'];
    select['search[value]'] = data.search['value'];
    select['start'] = data.start;

    let filter_row = $('#' + this.id + ' thead tr:eq(1) th');
    if ( $(filter_row).length > 0 ) {
        filter_row.each( function ( i ) {
            if ($(this).hasClass('filter-column')) {
                let val = $('select :selected', this).val();
                if (val !== '') {
                    select[$('select', this).attr('name')] = val;
                }
            }
        });
    }
    else if ( this.hasOwnProperty('colFilters') )
    {
        // if we dont have a dropdown row yet, we're at the pre first load stage - check to see
        // if we have any column filters specified in the link and if so apply those so they're included
        // in the initial data fetch
        for ( const idx of Object.keys( this.colFilters ) ) {
            if ( this.colFilters.hasOwnProperty( idx ) ) {
                select[idx] = this.colFilters[idx];
            }
        }
    }
}

slm.requestReview = function(siteId, detail='') {
    return $.ajax({
        url: slm.urls.reverse(
            'slm_edit_api:request_review-detail',
            {kwargs: {pk: siteId}}
        ),
        method: 'PUT',
        data: {detail: detail}
    });
}

slm.rejectReview = function(siteId, detail='') {
    return $.ajax({
        url: slm.urls.reverse(
            'slm_edit_api:reject_updates-detail',
            {kwargs: {pk: siteId}}
        ),
        method: 'PUT',
        data: {detail: detail}
    });
}

slm.publish = function(siteId) {
    return $.ajax({
        url: slm.urls.reverse('slm_edit_api:stations-detail', {kwargs: {'pk': siteId}}),
        data: {'publish': true},
        method: 'PATCH'
    });
}

slm.revert = function(siteId) {
    return $.ajax({
        url: slm.urls.reverse('slm_edit_api:stations-detail', {kwargs: {'pk': siteId}}),
        data: {'revert': true},
        method: 'PATCH'
    });
}

slm.rotateImage = function(degrees, fileId) {
    return $.ajax({
        url: slm.urls.reverse(
            'slm_edit_api:image-detail',
            {kwargs: {'pk': fileId}, query: {'rotate': degrees}})
    });
}

slm.deleteFile = function(station, fileId) {
    return $.ajax({
        url: slm.urls.reverse(
            'slm_edit_api:files-detail',
            {kwargs: {'site': station, 'pk': fileId}}
        ),
        method: 'DELETE'
    });
}

slm.publishFile = function(station, fileId, publish) {
    return $.ajax({
        url: slm.urls.reverse(
            'slm_edit_api:files-detail',
            {kwargs: {'site': station, 'pk': fileId}}
        ),
        method: 'PATCH',
        data: {
            'status': publish ?
                slm.SiteFileUploadStatus.PUBLISHED.value :
                slm.SiteFileUploadStatus.UNPUBLISHED.value
        }
    });
}

slm.updateFileBadges = function(delta) {
    let filesBadge = $('span.slm-files-badge');
    filesBadge.data(
        'slmFiles',
        Math.max(0, filesBadge.data('slmFiles') + delta)
    );
    filesBadge.html(filesBadge.data('slmFiles'));
    if (filesBadge.data('slmFiles') === 0) {
        filesBadge.hide();
    } else {
        filesBadge.show();
    }
}

slm.setFormFields = function(form, data) {
    // todo swap this with Form class - its much more robust.
    const toBool = function(value) {
        if (value === 'off' || !value) {
            return false;
        }
        return true;
    }
    for (const [field, value] of Object.entries(data)) {
        const select = form.find(`select[name="${field}"]`);
        select.find('option').prop('selected', false);
        const multiCheck = form.find(`input:checkbox[name="${field}"]`);
        if (select.length > 0) {
            for (const val of Array.isArray(value) ? value : [value]) {
                select.find(`option[value="${val}"]`).prop('selected', true);
            }
        } else if (multiCheck.length > 1) {
            for (const val of Array.isArray(value) ? value : [value]) {
                form.find(`input:checkbox[name="${field}"][value="${val}"]`).prop('checked', true);
            }
        } else {
            form.find(`input[name="${field}"], textarea[name="${field}"]`).val(value);
            form.find(`input:checkbox[name="${field}"]`).prop('checked', toBool(value));
        }
    }
}

slm.formToObject = function(form, fields=null) {
    /**
     * Why is it so hard to turn form data into json? FormData is very awkward
     * to work with fields with multiple selections.
     */
    let formData = new FormData(form.get(0));
    let data = {};
    let multiples = new Set();
    formData.forEach(function(value, key) {
        if (fields && !fields.includes(key)) {
            return;
        }
        let element = form.find(
            `input[name="${key}"], textarea[name="${key}"], select[name="${key}"]`
        );
        if (element.length > 1 || element.get(0).hasAttribute( 'multiple' )) {
            // special case for split date/times
            if (element.length === 2 && element.get(0).getAttribute('type') === 'date') {
                if (element.get(0).value) {
                    data[key] = `${element.get(0).value}T${element.get(1).value || "00:00"}Z`
                }
            } else {
                data[key] = formData.getAll(key);
            }
        } else {
            data[key] = value;
        }
    });
    const checkboxes = new Set();
    form.find('input:checkbox').each(function(idx, element) {
        const name = element.getAttribute('name');
        if (checkboxes.has(name)) {
            multiples.add(name);
        }
        checkboxes.add(name);
    });
    let notMult = '';
    for (const mult of multiples) {
        notMult += `[name!="${mult}"]`;
    }
    form.find(`${notMult}:checkbox`).each(function(idx, element) {
        data[element.getAttribute('name')] = $(element).prop('checked')
    });
    return data;
}

slm.stationFilterCallbacks = [];

slm.stationFilterChanged = function(filterParams) {
    for (const callback of slm.stationFilterCallbacks) {
        callback(filterParams);
    }
}

slm.hasParameters = function(query, ignored=[]) {
    for (const [key, value] of Object.entries(query)) {
        if (
            key === 'start' || key === 'length' || key === 'id' || ignored.includes(key)
        ) { continue; }
        if (Array.isArray(value)) {
            if (value.length > 0) { return true; }
        } else if (
            value !== null &&
            value !== '' &&
            typeof value !== 'undefined'
        ) { return true; }
    }
    return false;
}

slm.updateAlertBell = function(site) {
    let level = site.max_alert ? AlertLevel.get(site.max_alert) : null;
    let navBtn = $(`#select-${site.name}`);
    let bells = $(
        `#select-${site.name} .slm-alert-bell, #slm-station-nav .slm-alert-bell`
    );
    let current = AlertLevel.get(navBtn.data('slmAlert'));
    bells.removeClass('bi-bell-fill');
    bells.addClass('bi-bell');
    navBtn.data('slmAlert', null);
    if (current) {
        bells.removeClass(`${current.css}`);
    }
    if (level) {
        navBtn.data('slmAlert', level.value);
        bells.addClass(`${level.css}`);
        bells.removeClass('bi-bell');
        bells.addClass('bi-bell-fill');
        bells.show();
    } else {
        $(`#select-${site.name} .slm-alert-bell`).hide();
    }
}

slm.processing = function(btn) {
    btn.find('span.spinner-border').remove();
    $('body').css('cursor', 'progress');
    btn.append('<span class="ms-2 spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>');
    return function() {
        $('body').css('cursor', 'default');
        btn.find('span.spinner-border').remove();
    }
}

slm.isIterable = function(input) {
    if (input === null || input === undefined) { return false; }
    return typeof input[Symbol.iterator] === 'function';
}

slm.incrSectionNumber = function(versionString, incr=1) {
    if (versionString !== null && versionString !== '') {
        let numbers = versionString.split('.').map(Number);
        numbers[numbers.length - 1] += incr;
        return numbers.join('.');
    }
    return '';
}
