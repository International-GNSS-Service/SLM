class FormWidget extends slm.Persistable {

    #container;

    get container() {
        return this.#container;
    }

    constructor(container) {
        super(container.get(0).getAttribute('id'));
        this.#container = container;
    }

    changed() {
        /**
         * Deriving widgets should implement this callback which is invoked
         * when the underlying widget's state has changed.
         */
    }

}

slm.FormWidget = FormWidget;
