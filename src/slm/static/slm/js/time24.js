if (typeof slm === 'undefined' || slm == null) { var slm = {}; }

slm.time24Init = function(inputs = null) {

    inputs = inputs || $('fieldset.time-24hr');

    inputs.click(function() {
        //const timeSelect = $(this).siblings('div.time-select');
        const timeSelect = $(this).find('div.time-select');
        if (timeSelect.css('display') !== 'none') {
            toggleTimeSelectDropDown(timeSelect);
        }
    });

    inputs.keydown(function( event ) {
        //let timeSelect = $(this).siblings('div.time-select');
        if ($(this).attr('disabled') !== undefined) {
            return;
        }
        let timeSelect = $(this).find('div.time-select');
        let selected = $(this).find('span.time-input-selected');
        let currentTime = timeSelect.find('span.time-selected');
        let isMinutes = selected.hasClass('minutes');
        if (event.which === 39 || event.which === 37) {
            // left/right
            if (!currentTime.length) {
                if (selected.length > 0) {
                    selectSpanText(event.which === 39 ? selected.next() : selected.prev());
                } else {
                    selectSpanText(timeSelect.find('span.hours'));
                }
            } else {
                if (currentTime.parent().hasClass('minute-scroll')) {
                    if (event.which === 37) {
                        selectTime(timeSelect.find('div.hour-scroll > span.time-set'));
                        selectSpanText($(this).find('span.hours'));
                    }
                } else {
                    if (event.which === 39) {
                        selectTime(timeSelect.find('div.minute-scroll > span.time-set'));
                        selectSpanText($(this).find('span.minutes'));
                    }
                }
            }
            event.preventDefault();
        } else if (event.which === 38 || event.which === 40) {
            // up/down
            if (!currentTime.length) {
                currentTime = timeSelect.find(
                    `div.${ isMinutes ? "minute" : "hour"}-scroll > span.time-set`
                );
            } else {
                currentTime = event.which === 40 ? currentTime.next() : currentTime.prev();
            }
            selectTime(currentTime);
            selectSpanText(selected);
            event.preventDefault();
        } else if (event.which === 13) {
            // enter
            $(this).trigger("blur");
        } else if (event.which >= 48 && event.which <= 57) {
            // 0-9
            if (timeSelect.css('display') === 'none') {
                let num = event.which - 48;
                let numStr = num.toString();
                let keyState = selected.data('keyState');
                let max10s = isMinutes ? 5 : 2;
                let max1s = isMinutes ? 9 : 3;
                let skip;
                let skipWrite = false;
                if (!keyState) {
                    keyState = `0${numStr}`;
                    skip = num > max10s;
                } else if (keyState.length >= 2) {
                    skipWrite = num > max1s && parseInt(keyState[1]) === max10s;
                    keyState = `${keyState[1]}${numStr}`;
                    skip = true;
                }
                if (!skipWrite) {
                    selected.data('keyState', keyState);
                    selected.html(keyState);
                    selectTime(timeSelect.find(
                        `div.${isMinutes ? "minute" : "hour"}-scroll > span:contains('${keyState}')`
                    ))
                }
                if (skip) {
                    if (isMinutes) {
                        $(this).trigger('blur');
                    } else {
                        selectSpanText($(this).find('span.minutes'));
                    }
                } else {
                    selectSpanText(selected);
                }
            }
        }
    });

    const toggleTimeSelectDropDown = function(timeSelect) {
        if (timeSelect.css('display') === 'none') {
            timeSelect.css('display', 'flex');
            initScroll(timeSelect);
        } else {
            timeSelect.css('display', 'none');
        }
    }
    inputs.find('svg.clock-icon').click(function() {
        const timeInput = $(this).closest('fieldset.time-24hr');
        toggleTimeSelectDropDown(timeInput.find('.time-select'));
        //toggleTimeSelectDropDown(timeInput.siblings('.time-select'));
        timeInput.focus();
        return false;
    });

    //inputs.siblings('div.time-select').find(
    inputs.find('div.time-select').find(
        'div.hour-scroll > span, div.minute-scroll > span'
    ).click(function() {selectTime($(this))});

    inputs.blur(function(event) {
        if ($(event.relatedTarget).parents('div.time-select').length > 0) {
            $(this).focus();
            return false;
        }
        //let selectDiv = $(this).siblings('div.time-select');
        let selectDiv = $(this).find('div.time-select');
        selectDiv.css('display', 'none');
        selectDiv.find('span.time-selected').removeClass('time-selected');
        $(this).find('span.hours').data('keyState', null);
        $(this).find('span.minutes').data('keyState', null);
        $(this).find('span.time-input-selected').removeClass('time-input-selected');
        window.getSelection().removeAllRanges();
    });

    inputs.focusin(function() {
        selectSpanText($(this).find('span.hours'));
    });

    const selectSpanText = function(span) {
        if (!span.length) {
            return;
        }
        span.addClass('time-input-selected');
        span.siblings('span').removeClass('time-input-selected');
        let range, selection;
        if (window.getSelection && document.createRange) {
            selection = window.getSelection();
            range = document.createRange();
            range.selectNodeContents(span.get(0));
            selection.removeAllRanges();
            selection.addRange(range);
        } else if (document.selection && document.body.createTextRange) {
            range = document.body.createTextRange();
            range.moveToElementText(span.get(0));
            range.select();
        }
    }

    const initScroll = function(timeSelect) {
        const hourScroll = timeSelect.find('div.hour-scroll');
        setScroll(hourScroll, hourScroll.find('span.time-set'), true);
        const minuteScroll = timeSelect.find('div.minute-scroll');
        setScroll(minuteScroll, minuteScroll.find('span.time-set'), true);
    }

    const setScroll = function(scroll, span, top=false) {
        const selectTop = scroll.get(0).getBoundingClientRect().y;
        const selectBottom = selectTop + scroll.height();
        const spanTop = span.get(0).getBoundingClientRect().y;
        if (spanTop > (selectBottom - 5)) {
            scroll.get(0).scrollTop += (spanTop - selectBottom) + (top ? scroll.height() : span.height() + 5);
        } else if (spanTop < selectTop) {
            scroll.get(0).scrollTop -= selectTop - spanTop;
        }
    }

    const selectTime = function(timeSpan) {
        if (!timeSpan.length) { return; }
        const timeSelect = timeSpan.closest('div.time-select');
        //const timeInput = timeSelect.siblings('div.time-24hr');
        const timeInput = timeSelect.closest('fieldset.time-24hr');
        const column = timeSpan.closest('div.time-scroll');
        timeSpan.siblings('span.time-set').removeClass('time-set');
        timeSpan.addClass('time-set');
        timeSelect.find('span.time-selected').removeClass('time-selected');
        timeSpan.addClass('time-selected');
        setScroll(column, timeSpan);
        setTime(timeInput, timeSelect);
    }

    const setTime = function(timeInput, timeSelect) {
        let hours = timeSelect.find('div.hour-scroll > span.time-set').text();
        let minutes = timeSelect.find('div.minute-scroll > span.time-set').text();
        timeInput.find('span.hours').html(hours);
        timeInput.find('span.minutes').html(minutes);
        if (hours !== null && minutes !== null) {
            timeInput.find('input[type="time"]').val(
                `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:00`
            );
        }
    }

    inputs.find('input[type="time"]').each(function() {
       let value = $(this).val().split(':');
       if (value[0]) {
           //const timeSelect = $(this).closest('fieldset.time-24hr').siblings('div.time-select');
           const timeSelect = $(this).closest('fieldset.time-24hr').find('div.time-select');
           selectTime(timeSelect.find(`div.hour-scroll > span:contains('${value[0]}')`));
           selectTime(timeSelect.find(`div.minute-scroll > span:contains('${value[1]}')`));
       }
    });
}
