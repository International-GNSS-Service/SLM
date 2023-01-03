// https://github.com/devbridge/jQuery-Autocomplete
$(document).ready(function() {
    $('input[data-slm-autocomplete]').each(function() {
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
});
