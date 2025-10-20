class Form extends slm.Persistable {
    /**
     * This class encapsulates reading and writing json data to/from html forms.
     * This is less trivial than you might assume and there are some special case
     * SLM field behavior (namely composition/decomposition) and custom input
     * widgets that are handled.
     */

    element;
    #initial;  // the "clear" state of the form
    fields;
    widgets;  // object keyed on field name where the values are widgets
    last; // last serialized data

    #multi;
    #composite;

    #changeCallbacks;

    static ELEMENTS = ['input', 'select', 'textarea'];

    static toBool = function(value) {
        /**
         * Convert a value to a boolean. Special string cases are handled.
         */
        if (typeof value === 'string' || value instanceof String) {
            value = value.toLowerCase();
            if (['yes', 'y', 'true', '1', 'on'].includes(value)) {
                return true;
            } else if (['no', 'n', 'false', '0', 'off'].includes(value)) {
                return false;
            }
            else {
                return null;
            }
        }
        return Boolean(value);
    }

    static differs = function(state1, state2) {
        /**
         * Returns true if the given form states differ, false otherwise.
         */
        for (const [key, value] of Object.entries(state1)) {
            if (state2.hasOwnProperty(key)) {
                if (Array.isArray(value)) {
                    if (
                        Array.isArray(state2[key]) &&
                        value.length === state2[key].length
                    ) {
                        for (let idx = 0; idx < value.length; idx++) {
                            if (value[idx] !== state2[key][idx]) {
                                return true;
                            }
                        }
                    } else {
                        return true;
                    }
                } else if (
                    Array.isArray(state2[key]) ||
                    value !== state2[key]
                ) { return true; }
            }
        }
        return false;
    }

    static stripNulls = function(data) {
        /**
         * Strip empty arrays and values from the query data.
         * @type {{}}
         */
        const stripped = {};
        for (const [key, value] of Object.entries(data)) {
            if (value) { stripped[key] = value;}
        }
        return stripped;
    }

    static toQueryString = function(data) {
        /**
         * Convert query data to a url query string. No ? will be added
         * to the front. This will strip nulls.
         */
        const params = [];
        for (const [key, value] of Object.entries(data)) {
            if (value) {
                params.push(`${key}=${value}`);
            }
        }
        return params.join('&');
    }

    get excluded() {
        /** fields excluded from persistence */
        return ['csrfmiddlewaretoken'];
    }

    get initial() {
        /**
         * Returns a copy of the initial form settings (i.e. the "clear" state
         * of the form.
         */
        return JSON.parse(JSON.stringify(this.#initial));
    }

    set initial(initial) {
        /**
         * Set the initial (i.e. clear) state of the form - some fields may
         * have default values.
         *
         * The initial state of each field is determined in order of precedence
         * by:
         *
         * 1) The value defined for the field in data-slm-initial on the form
         *    element.
         * 2) The current value of the form on initialization for any excluded
         *    fields.
         * 3) The default (see default()) value for field type.
         */
        this.#initial = initial;
        if (this.excluded.length > 0) {
            const data = this.data;
            for (const field of this.excluded) {
                if (this.fields.has(field)) {
                    this.#initial[field] = data[field];
                }
            }
        }
        for (const field of this.fields) {
            if (!this.#initial.hasOwnProperty(field)) {
                this.#initial[field] = this.default(field);
            }
        }
    }

    get data() {
        /**
         * Get the JSON representing the form.
         *
         * If multiple input elements exist with the same name and different
         * types, that is considered a composite field. It will be combined
         * into a single field using compose. The reverse operation is
         * decompose.
         *
         * Multiple input elements that exist with the same name and the same
         * type will be turned into arrays where the array elements are the
         * values of the activated elements (checkboxes and selects).
         *
         */
        const data = {};

        const coerceValue = function(fieldName, value) {
            if (!this.isMulti(fieldName) && this.type(fieldName) === 'checkbox') {
                return Form.toBool(value);
            }
            return value;
        }.bind(this);

        // flatten name/value objects into name: value or name: array[values]
        for (const field of this.element.serializeArray()) {
            let value = coerceValue(field.name, field.value);
            if (this.isMulti(field.name)) {
                if (Array.isArray(data[field.name])) {
                    data[field.name].push(value);
                } else {
                    data[field.name] = [value];
                }
            } else {
                if (Object.hasOwn(data, field.name)) {
                    const current = data[field.name];
                    if (Array.isArray(current)) {
                        current.push(value);
                    } else {
                        data[field.name] = [current, value];
                    }
                } else {
                    data[field.name] = value;
                }
            }
        }

        // compose any composite fields
        for (const [field, value] of Object.entries(data)) {
            if (this.isComposite(field)) {
                data[field] = this.compose(this.type(field), value);
            }
        }

        for (const field of this.fields) {
            if (!data.hasOwnProperty(field)) {
                data[field] = this.default(field);
            }
        }

        return data;
    }

    set data(data) {
        /**
         * Populates a form from the given json object. Keys should correspond
         * to element names. Values are either singular or are arrays. Array
         * values are expected to correspond to the value attributes of select
         * options or checkboxes.
         *
         * If a form has multiple fields of different types with the same name
         * that field value is decomposed using decompose() into a value for
         * each input element.
         *
         * @type {any}
         */
        
        // form updates must be total - any missing fields will be defaulted
        data = Object.assign(this.initial, data);

        const setField = function(ipt, value) {
            switch (ipt.prop('type')) {
                case 'radio':
                case 'checkbox':
                    ipt.each(function () {
                        $(this).prop('checked', Form.toBool(value));
                    });
                    break;
                default:
                    ipt.val(value);
            }
        }

        $.each(data, function (field, value) {
            const ipt = this.field(field);
            if (Array.isArray(value)) {
                switch (ipt.prop('type')) {
                    case 'select': case 'select-multiple':
                        const selected = [];
                        for (const val of value) { selected.push(`option[value="${val}"]`); }
                        ipt.find(selected.join(', ')).prop('selected', true);
                        ipt.find('option').not(selected).prop('selected', false);
                        break;
                    case 'checkbox':
                        let checked = [];
                        for (const val of value) { checked.push(`[name="${field}"][value="${val}"]:checkbox`); }
                        checked = this.element.find(checked.join(', '));
                        checked.prop('checked', true);
                        this.element.find(`[name="${field}"]:checkbox`).not(checked).prop('checked', false);
                        break;
                    case 'number':
                        if (value.length === ipt.length) {
                            let idx = 0;
                            for (const val of value) { $(ipt[idx++]).val(val); }
                            break;
                        }
                    default:
                        throw TypeError(`Type mismatch: ${value} ${ipt.prop('type')}`);
                }
            } else if (ipt.length > 1) {
                const types = [];
                ipt.each(function () { types.push($(this).prop('type')); });
                const values = this.decompose(types, value);
                ipt.each((i, e) => setField($(e), values[i]));
            } else { setField(ipt, value); }
        }.bind(this));

        for (const widget of Object.values(this.widgets)) {
            widget.changed();
        }
    }
    
    constructor(element) {
        super(element);
        this.element = element;
        this.#composite = {};
        this.#multi = new Set();
        this.#changeCallbacks = [];
        this.widgets = {};
        
        // Step one is to determine which names are not unique. These fields are
        // either array-value fields or if the types differ they are composed.
        this.fields = new Set();
        this.element.find(Form.ELEMENTS.join(',')).each((idx, ipt) => {
            this.fields.add($(ipt).prop('name'));
        })
        for (const field of this.fields) {
            const inputs = this.element.find(this.field(field));
            if (inputs.data('widget')) {
                this.widgets[field] = inputs.data('widget');
            }
            if (inputs.length > 1) {
                const types = new Set();
                inputs.each((idx, element) => {
                    types.add($(element).prop('type'));
                });
                types.size > 1 ? this.#composite[field] = types : this.#multi.add(field);
            } else if (inputs.get(0).hasAttribute('multiple')) {
                this.#multi.add(field);
            }
        }

        if (this.element.data('slmInitial')) {
            this.initial = this.element.data('slmInitial');
        } else {
            this.initial = {};
        }

        this.element.data('slmForm', this);

        this.element.find(':input').on('change', function() {
            const data = this.data;
            if (Form.differs(data, this.last)) {
                for (const changed of this.#changeCallbacks) { changed(this); }
                this.last = data;
            }
        }.bind(this));

        this.last = this.data;
    }

    decompose(types, value) {
        const typeList = Array.isArray(types) ? types : Array.from(types);
        if (typeList.length === 2 && typeList[0] === 'date' && typeList[1] === 'time') {
                if (value) { return value.split('T'); }
                return ['', ''];
        }
        throw TypeError(`Unexpected decomposition types: ${types}`);
    }

    compose(types, inputs) {
        const typeList = Array.isArray(types) ? types : Array.from(types);
        if (typeList.length === 2 && typeList[0] === 'date' && typeList[1] === 'time') {
            return `${inputs[0]}T${inputs[1] || "00:00"}Z`                
        }
        throw TypeError(`Unexpected composition types: ${[...typeList].join(', ')}`);
    }

    clear() {
        this.data = this.initial;
    }

    isComposite(field) {
        return this.#composite.hasOwnProperty(field);
    }

    isMulti(field) {
        return this.#multi.has(field);
    }
    
    type(field) {
        if (this.isComposite(field)) {
            return this.#composite[field];
        }
        return this.field(field).prop('type');
    }
    
    default(field) {
        if (this.isMulti(field)) {
            return [];
        } else if (this.isComposite(field)) {
            return this.decompose(this.type(field), '');
        }
        switch(this.type(field)) {
            case 'checkbox':
            case 'radio':
                return false;
            default:
                return '';
        }
    }

    field(name) {
        return this.element.find(
            Form.ELEMENTS.join(`[name="${name}"],`) + `[name="${name}"]`
        );
    }

    hasChanged() {
        /**
         * Returns true if this form differs from its initial "clear" state and
         * false otherwise.
         */
        return Form.differs(this.data, this.initial);
    }

    persist() {
        /**
         * Persist this form's current state to session memory.
         */
        const current = this.data;
        // never persist excluded fields
        for (const field of this.excluded) {
            if (current.hasOwnProperty(field)) {
                delete current[field];
            }
        }
        this.persisted = current;
        for (const widget of Object.values(this.widgets)) {
            widget.persist();
        }
    }

    revive() {
        /**
         * Revive this form's current state from session memory, if it has
         * been persisted.
         */
        this.data = this.persisted;
        for (const widget of Object.values(this.widgets)) {
            widget.revive();
        }
    }

    onChange(callback) {
        this.#changeCallbacks.push(callback);
    }
}

slm.Form = Form;
