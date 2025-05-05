if (typeof slm === 'undefined' || slm == null) { var slm = {}; }

class Persistable {
    /**
     * A simple interface defining a persistable component. Data is persisted
     * in session memory.
     */

    key;

    get persisted() {
        const store = sessionStorage.getItem(this.key);
        if (store) {
            return JSON.parse(sessionStorage.getItem(this.key));
        }
        return {}
    }

    set persisted(data) {
        sessionStorage.setItem(this.key, JSON.stringify(data));
    }

    constructor(key) {
        this.key = key;
    }

    persist() {/* Deriving classes define their own persist logic */}

    revive() {
        /*
         * Deriving classes define their own revival logic, this method
         * should restore persisted state to the component
         */
    }
}

slm.Persistable = Persistable;
