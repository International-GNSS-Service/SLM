(function($) {
    $(document).ready(function() {
        $('.view-file').on('click', function(e) {
            e.preventDefault();
            const url = $(this).data('url');
            const modal = $('<div class="modal"/>').css({
                position: 'fixed',
                top: '10%',
                left: '10%',
                width: '80%',
                height: '80%',
                background: '#fff',
                border: '1px solid #ccc',
                padding: '20px',
                overflow: 'auto',
                zIndex: 10000
            }).appendTo('body');

            const overlay = $('<div class="modal-overlay"/>').css({
                position: 'fixed',
                top: 0, left: 0, right: 0, bottom: 0,
                background: 'rgba(0, 0, 0, 0.5)',
                zIndex: 9999
            }).appendTo('body');
            
            modal.append(
                $('<span class="close-modal">&times;</span>').css({
                    position: 'absolute',
                    top: '10px',
                    right: '15px',
                    fontSize: '24px',
                    fontWeight: 'bold',
                    cursor: 'pointer',
                })
            );
            modal.append('<div class="modal-content"></div>');

            $.get(url, function(data) {
                let content;

                // Check if response is an XML Document
                const isXml = data instanceof XMLDocument && data.documentElement;
            
                if (isXml) {
                    const xmlString = new XMLSerializer().serializeToString(data.documentElement);
                    const escaped = $('<div/>').text(xmlString).html();  // escape XML
                    content = `<pre style="white-space: pre-wrap; word-break: break-word;">${escaped}</pre>`;
                } else {
                    // Fallback for plain text or JSON
                    const escaped = $('<div/>').text(data).html();  // escape if string
                    content = `<pre style="white-space: pre-wrap; word-break: break-word;">${escaped}</pre>`;
                }
                modal.find('.modal-content').html(content);
            });

            modal.on('click', '.close-modal', function() {
                modal.remove();
                overlay.remove();
            });
        });
    });
})(django.jQuery);
