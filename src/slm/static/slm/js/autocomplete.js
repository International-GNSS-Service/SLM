class AutoComplete extends slm.FormWidget {
    /**
     * https://api.jqueryui.com/autocomplete/
     *
     * Expects the following data parameters on the auto complete container:
     *
     * data-service-url: (required) The url to fetch suggestions from ajax
     * data-search-param: (required) The url query parameter to use for the search string
     * data-label-param: (optional) The property to use as the label (default: search-param)
     * data-value-param: (optional) The property to use as the value (default: label-param)
     * data-renderSuggestion: (optional) A javascript function body accepting an obj argument and
     *  returning a string label to use for the suggestion.
     *
     *  When providing a render suggestion, text that is searchable should be
     *  wrapped in <span class="matchable"></span>
     */

    textInput;
    formField;

    paramName;
    serviceUrl;
    valueParam;
    selected;

    // if theres a full match on the first suggestion when the field is
    // defocused (enter or click away) we set the value to that first match.
    newResponse; // toggle used to only check the first menu item
    fullMatch;
    firstSuggestion;

    renderSuggestion(suggestion) {
        return `<span class="matchable">${suggestion[this.labelParam]}</span>`;
    }

    inputUpdated() {
        /**
         * When a user changes search text, we unset the set value if one is
         * set, remove any html, reset the search box to the raw search string
         * and set the cursor to the end.
         */
        const label = this.textInput.html();
        const searchStr = this.textInput.find('.matchable').text();
        const value = this.formField.val();
        if (value) {
            if (label !== this.selected[value]) {
                this.remove(this.formField.val());
                this.textInput.html(searchStr);
                let sel = window.getSelection();
                sel.selectAllChildren(this.textInput.get(0));
                sel.collapseToEnd();
            }
        }
    }

    getSuggestion(value) {
        /**
         * Return the suggestion exactly matching the value.
         */
        const query = {};
        query[this.valueParam] = value;
        let suggestion = null;
        $.ajax({
            url: this.serviceUrl,
            data: query,
            async: false
        }).done(
            function(data) {
                if (data.length > 0) {
                    suggestion = this.makeSuggestion(data[0]);
                }
            }.bind(this)
        ).fail(function(jqXHR) {console.log(jqXHR);});
        return suggestion;
    }

    makeSuggestion(suggestion) {
        return {
            label: this.renderSuggestion(suggestion),
            value: suggestion[this.valueParam],
            basic: suggestion[this.labelParam]
        }
    }

    filterResponse(data) {
        this.inputUpdated();
        const suggestions = [];
        this.newResponse = true;
        this.fullMatch = false;
        if (data.length > 0) {
            this.firstSuggestion = this.makeSuggestion(data[0]);
        } else {
            this.firstSuggestion = null;
        }
        for (const suggestion of data) {
            if (this.selected.hasOwnProperty(
                suggestion[this.valueParam].toString()
            )) {
                continue;
            }
            suggestions.push(this.makeSuggestion(suggestion));
        }
        return suggestions;
    }

    constructor(options) {
        super(options.container);
        this.textInput = this.container.find('.search-input');
        this.formField = this.container.find(':input').first();
        this.selected = {};
        if (this.textInput.val()) {
            this.selected[this.textInput.val()] = this.textInput.html();
        }
        this.serviceUrl = this.textInput.data('serviceUrl');
        this.source = this.textInput.data('source');
        this.searchParam = this.textInput.data('searchParam');
        this.labelParam = this.textInput.data('labelParam') || this.searchParam;
        this.valueParam = this.textInput.data('valueParam') || this.labelParam;
        this.queryParams = this.textInput.data('queryParams') || {};
        this.menuClass = this.textInput.data('menuClass') || '';

        if (this.textInput.data('renderSuggestion')) {
            this.renderSuggestion = new Function(
                'obj',
                this.textInput.data('renderSuggestion')
            );
        }

        // blur the input when enter is pressed
        this.textInput.keypress(function(e) {
            if (e.which === 13) {
                $(this).trigger('blur');
            }
        });

        this.textInput.blur(() => {
            if (this.fullMatch && this.firstSuggestion) {
                this.add(this.firstSuggestion);
            }
        });

        this.autocomplete = this.textInput.autocomplete({
            delay: 250,
            minLength: 0,
            source: this.serviceUrl ? (request, response) => {
                const data = this.queryParams;
                data[this.searchParam] = request.term;
                $.ajax({url: this.serviceUrl, data: data}).done(
                    function(data) {
                        response(this.filterResponse(data));
                    }.bind(this)
                ).fail(function(jqXHR) {console.log(jqXHR);});
            }: (request, response) => {
                const data = $.ui.autocomplete.filter(this.source, request.term);
                response(
                    this.filterResponse(
                        data
                    )
                );
            },
            change: function(event, ui) {
                this.formField.trigger('change');
            }.bind(this),
            select: function(event, ui) {
                this.add(ui.item);
                event.preventDefault();
            }.bind(this),
            focus: function(event, ui) {
                this.textInput.html(ui.item.basic);
                return false;
            }.bind(this),

        }).bind('focus', function() { $(this).autocomplete('search'); } );

        const checkFullMatch = function(text, term) {
            this.fullMatch |= text.toUpperCase() === term.toUpperCase();
            if (!this.fullMatch) {
                // special case for (text)
                if (text.startsWith('(')) {
                    text = text.substring(1);
                }
                if (text.endsWith(')')) {
                    text = text.substring(0, text.length-1);
                }
                this.fullMatch |= text.toUpperCase() === term.toUpperCase();
            }
        }.bind(this);

        const newResponse = function(newResponse=null) {
            if (newResponse !== null) {
                this.newResponse = newResponse;
            }
            return this.newResponse;
        }.bind(this)

        this.autocomplete.data('ui-autocomplete')._renderItem = function (ul, item) {
            const label = $(`<div>${item.label}</div>`);
            if (this.term) {
                label.find('span.matchable').each((idx, child) => {
                    if (newResponse()) {
                        checkFullMatch($(child).text(), this.term);
                    }
                    $(child).html(
                        String($(child).text()).replace(
                            new RegExp(this.term, 'gi'),
                        "<span class='autocomplete-match'>$&</span>")
                    );
                });
            }
            newResponse(false);
            return $('<li></li>')
                .data('item.ui-autocomplete', item)
                .append(label)
                .appendTo(ul);
        };

        if (this.menuClass) {
            const menuClass = this.menuClass;
            this.autocomplete.data('ui-autocomplete')._renderMenu = function (ul, items) {
                const that = this;
                $.each(items, function (index, item) {
                    that._renderItemData(ul, item);
                });
                $(ul).addClass(menuClass);
            }
        }
    }

    add(item) {
        this.remove(this.formField.val());
        this.selected[item.value.toString()] = item.label;
        this.formField.val(item.value.toString());
        this.textInput.html(item.label);
    }

    remove(value) {
        value = value.toString();
        if (this.selected.hasOwnProperty(value)) {
            delete this.selected[value];
        }
        this.formField.val('');
        this.textInput.html('');
    }

    clear() {
        for (const value of Object.keys(this.selected)) { this.remove(value, false); }
    }

    persist() {
        this.persisted = this.selected;
    }

    revive() {
        if (this.persisted) {
            this.clear();
            for (const [value, label] of Object.entries(this.persisted)) {
                this.add({value: value, label: label});
            }
        }
    }

    changed() {}
}

class AutoCompleteMultiple extends AutoComplete {
    /**
     * https://github.com/devbridge/jQuery-Autocomplete
     *
     * Expects the following data parameters on the auto complete container:
     *
     * data-service-url: (required) The url to fetch suggestions from via ajax
     * data-search-param: (required) The url query parameter to use for the search string
     * data-label-param: (optional) The property to use as the label (default: search-param)
     * data-value-param: (optional) The property to use as the value (default: label-param)
     * data-renderSuggestion: (optional) A javascript function body accepting an obj argument and
     *  returning a string label to use for the suggestion.
     *
     *  When providing a render suggestion, text that is searchable should be
     *  wrapped in <span class="matchable"></span>
     */

    display;

    inputUpdated() { };

    constructor(options) {
        super(options);
        this.display = this.container.find('.select-display');
        this.selected = {};
        this.formField.find('option:selected').each(
            (idx, opt) => { this.selected[$(opt).val()] = $(opt).html(); }
        );

        this.display.find(`div.autocomplete-selection span:last-child`).click(function(event) {
            this.remove($(event.target).closest('div.autocomplete-selection').data('value'));
        }.bind(this));
    }

    add(item, trigger=true) {
        this.textInput.html('');
        this.selected[item.value.toString()] = item.label;
        if (this.formField.find(`option[value="${item.value}"]`).length === 0) {
            this.formField.prepend($(
                `<option value="${item.value}" selected>${item.label}</option>`
            ));
        }
        if (this.display.find(`div.autocomplete-selection[data-value="${item.value}"]`).length === 0) {
            this.display.prepend(
                `<div class="autocomplete-selection" data-value="${item.value}">${item.label}<span></span></div>`
            );
        }
        this.display.find(`div.autocomplete-selection[data-value="${item.value}"] span:last-child`).click(function() {
            this.remove(item.value);
        }.bind(this));
    }

    remove(value, trigger=true) {
        value = value.toString();
        if (this.selected.hasOwnProperty(value)) {
            delete this.selected[value];
        }
        this.formField.find(`option[value="${value}"]`).remove();
        this.display.find(`div.autocomplete-selection[data-value="${value}"]`).remove();
    }

    changed() {
        /**
         * The underlying select has been updated - we must refresh the
         * component to match it
         */
        const selected = this.formField.find('option:selected');
        if (selected.length === 0) { return this.clear(); }
        /* todo - only clear case handled above
        selected.each(
            (idx, opt) => { this.selected[$(opt).val()] = $(opt).html(); }
        );
         */
    }
}


slm.AutoComplete = AutoComplete;
slm.AutoCompleteMultiple = AutoCompleteMultiple;
