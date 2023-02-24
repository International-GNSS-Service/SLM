// https://github.com/devbridge/jQuery-Autocomplete

export class AutoComplete {
    /**
     * Expects the following data parameters on the auto complete container:
     *
     * data-service-url: (required) The url to fetch suggestions from via ajax
     * data-search-param: (required) The url query parameter to use for the search string
     * data-label-param: (optional) The property to use as the label (default: search-param)
     * data-value-param: (optional) The property to use as the value (default: label-param)
     * data-renderSuggestion: (optional) A javascript function body accepting an obj argument and
     *  returning a string label to use for the suggestion.
     */

    container;
    textInput;
    display;
    select;

    paramName;
    serviceUrl;
    valueParam;
    renderSuggestion;

    selected;

    get persisted() {
        const store = sessionStorage.getItem(this.container.attr('id'));
        if (store) {
            return JSON.parse(sessionStorage.getItem(this.container.attr('id')));
        }
        return {}
    }

    constructor(options) {
        this.container = options.container;
        this.textInput = options.container.find('.search-input');
        this.display = options.container.find('.select-display');
        this.select = options.container.find('select');
        this.selected = {};
        this.select.find('option:selected').each(
            (idx, opt) => { this.selected[$(opt).val()] = $(opt).html(); }
        );

        this.serviceUrl = this.container.data('serviceUrl');
        this.searchParam = this.container.data('searchParam');
        this.labelParam = this.container.data('labelParam') || this.searchParam;
        this.valueParam = this.container.data('valueParam') || this.labelParam;
        this.renderSuggestion = this.container.data('renderSuggestion') || null;
        if (this.renderSuggestion) {
            this.renderSuggestion = new Function('obj', this.renderSuggestion);
        }

        this.autocomplete = this.textInput.autocomplete({
            delay: 250,
            minLength: 0,
            source: function(request, response) {
                const data = {};
                data[this.searchParam] = request.term;
                $.ajax({url: this.serviceUrl, data: data}).done(
                    function(data) {
                        const suggestions = [];
                        for (const suggestion of data) {
                            if (this.selected.hasOwnProperty(suggestion[this.valueParam].toString())) {
                                continue;
                            }
                            suggestions.push({
                                label: this.renderSuggestion ? this.renderSuggestion(suggestion) : suggestion[this.labelParam],
                                value: suggestion[this.valueParam],
                                basic: suggestion[this.labelParam]
                            });
                        }
                        response(suggestions);
                    }.bind(this)
                ).fail(function(jqXHR) {console.log(jqXHR);});
            }.bind(this),
            select: function(event, ui) {
                this.add(ui.item);
                event.preventDefault();
                this.textInput.html('');
            }.bind(this),
            focus: function(event, ui) {
                this.textInput.html(ui.item.basic);
                return false;
            }.bind(this)
        }).bind('focus', function() { $(this).autocomplete('search'); } )
            .data('ui-autocomplete')._renderItem = function (ul, item) {
                const newText = String(item.label).replace(
                        new RegExp(this.term, 'gi'),
                        "<span class='autocomplete-match'>$&</span>");

                return $('<li></li>')
                    .data('item.ui-autocomplete', item)
                    .append(`<div>${newText}</div>`)
                    .appendTo(ul);
            };

        this.display.find(`div.autocomplete-selection span`).click(function(event) {
            this.remove($(event.target).closest('div.autocomplete-selection').data('value'));
        }.bind(this));
    }

    add(item) {
        this.selected[item.value.toString()] = item.label;
        if (this.select.find(`option[value="${item.value}"]`).length === 0) {
            this.select.prepend($(
                `<option value="${item.value}" selected>${item.label}</option>`
            ));
        }
        if (this.display.find(`div.autocomplete-selection[data-value="${item.value}"]`).length === 0) {
            this.display.prepend(
                `<div class="autocomplete-selection" data-value="${item.value}">${item.label}<span></span></div>`
            );
        }
        this.display.find(`div.autocomplete-selection[data-value="${item.value}"] span`).click(function() {
            this.remove(item.value);
        }.bind(this));
    }

    remove(value) {
        value = value.toString();
        if (this.selected.hasOwnProperty(value)) {
            delete this.selected[value];
        }
        this.select.find(`option[value="${value}"]`).remove();
        this.display.find(`div.autocomplete-selection[data-value="${value}"]`).remove();
    }

    clear() {
        for (const value of Object.keys(this.selected)) { this.remove(value); }
    }

    persist() {
        sessionStorage.setItem(
            `${this.container.attr('id')}`,
            JSON.stringify(this.selected)
        );
    }

    revive() {
        this.clear();
        for (const [value, label] of Object.entries(this.persisted)) {
            this.add({value: value, label: label});
        }
    }
}
