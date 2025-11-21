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

        $('.edit-file').on('click', function(e) {
            e.preventDefault();
            const url = $(this).data('url');
            const filename = $(this).data('filename');

            const modal = $('<div class="modal"/>').css({
                position: 'fixed',
                top: '10%',
                left: '10%',
                width: '80%',
                height: '80%',
                background: '#fff',
                border: '1px solid #ccc',
                padding: '20px',
                overflow: 'hidden',
                boxSizing: 'border-box',
                zIndex: 10000
            }).appendTo('body');

            const overlay = $('<div class="modal-overlay"/>').css({
                position: 'fixed',
                top: 0, left: 0, right: 0, bottom: 0,
                background: 'rgba(0, 0, 0, 0.5)',
                zIndex: 9999
            }).appendTo('body');

            // Header
            const header = $('<div/>').css({
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: '10px'
            });

            const title = $('<h3>Edit file</h3>').css({
                margin: 0
            });

            const buttonBar = $('<div/>');

            const cancelBtn = $('<button type="button">Cancel</button>').css({
                marginRight: '8px'
            });

            const saveBtn = $('<button type="button">Save</button>');

            buttonBar.append(cancelBtn, saveBtn);
            header.append(title, buttonBar);
            modal.append(header);

            // Textarea
            const textarea = $('<textarea class="file-editor"></textarea>').css({
                width: '100%',
                height: 'calc(100% - 70px)',
                boxSizing: 'border-box',
                fontFamily: 'monospace',
                fontSize: '13px',
                whiteSpace: 'pre',
                overflow: 'auto'
            });

            modal.append(textarea);

            // Load file
            $.get(url, function(data) {
                let text;
                const isXml = data instanceof XMLDocument && data.documentElement;

                if (isXml) {
                    text = new XMLSerializer().serializeToString(data.documentElement);
                } else {
                    text = typeof data === 'string' ? data : String(data);
                }

                textarea.val(text);
            });

            function closeModal() {
                modal.remove();
                overlay.remove();
            }

            cancelBtn.on('click', closeModal);
            overlay.on('click', closeModal);

            saveBtn.on('click', function() {
                const content = textarea.val();
                const blob = new Blob([content], { type: 'text/plain' });
                const formData = new FormData();
                formData.append('file', blob, filename);
                $.ajax({
                    url: url,
                    method: 'PATCH',
                    data: formData,
                    processData: false,
                    contentType: false,
                    headers: {
                        'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                    },
                    success: function() {
                        closeModal();
                    },
                    error: function(xhr) {
                        alert('Error saving file: ' + xhr.status + ' ' + xhr.statusText);
                    }
                });
            });
        });
    });
})(django.jQuery);
