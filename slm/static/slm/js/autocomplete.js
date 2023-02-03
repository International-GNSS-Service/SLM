// https://github.com/devbridge/jQuery-Autocomplete
if (typeof slm === 'undefined' || slm == null) { var slm = {}; }

slm.initAutoCompletes = function(inputs = null) {
    const autoInputs = inputs === null ? $('input[data-slm-autocomplete]') : inputs;
    autoInputs.each(function() {
        $(this).autocomplete({
            minChars: 0,
            serviceUrl: $(this).data('serviceUrl'),
            dataType: 'json',
            paramName: $(this).data('paramName'),
            transformResult: function(response) {
                return {
                    suggestions: $.map(response, function(dataItem) {
                        return dataItem.model;
                    })
                };
            }
        });
    });
}

