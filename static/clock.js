function get_utc_unix_timestamp(date)
{
    let local_unix_timestamp = date.getTime() / 1000;
    let timezone_offset_seconds = date.getTimezoneOffset() * 60;
    return parseInt(local_unix_timestamp + timezone_offset_seconds);
}

window.addEventListener('load', function() {
    const get_phase = function() {
        const start_time = competition_start_time;
        const end_time = competition_end_time;
        const current_time = get_utc_unix_timestamp(new Date(Date.now()));

        if (current_time < start_time) {
            return -1;
        } else if (start_time <= current_time && current_time < end_time) {
            return 0;
        } else {
            return 1;
        }
    };

    const format_int = function(x, n) {
        let s = parseInt(x).toString();
        if (s.length < n) {
            s = '0'.repeat(n - s.length) + s;
        }
        return s;
    };

    const format_time_interval = function(days, hours, minutes, seconds) {
        if (days == 0) {
            return `${hours}:${format_int(minutes,2)}:${format_int(seconds,2)}`;
        } else {
            return `${days} ${locale_messages['days']} ${hours}:${format_int(minutes,2)}:${format_int(seconds,2)}`;
        }
    };

    const update_function = function() {
        const clock = document.getElementById('ctfhost-clock');
        const start_time = competition_start_time;
        let current_phase = get_phase();
        if (current_phase != init_phase) {
            clock.classList.add('w3-yellow');
            if (current_phase == 0) {
                clock.innerHTML = locale_messages['clock_started_reload'];
            } else {
                clock.innerHTML = locale_messages['clock_finished_reload'];
            }
            return;
        }
        const end_time = competition_end_time;
        const current_time = get_utc_unix_timestamp(new Date(Date.now()));
        let delta_time = end_time - current_time;
        if (current_time < start_time) {
            clock.innerHTML = locale_messages['clock_not_started'];
        } else if (delta_time <= 0) {
            clock.innerHTML = locale_messages['clock_finished'];
        } else {
            const seconds = delta_time % 60;
            delta_time = parseInt(delta_time / 60);
            const minutes = delta_time % 60;
            delta_time = parseInt(delta_time / 60);
            const hours = delta_time % 24;
            delta_time = parseInt(delta_time / 24);
            const days = delta_time;

            clock.innerHTML = format_time_interval(days, hours, minutes, seconds);
        }
    };

    const init_phase = get_phase();

    update_function();
    setInterval(update_function, 1000);
});
