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
        const delta_time = end_time - current_time;
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
            if (days > 0) {
                clock.innerHTML = `${days}:${hours}:${minutes}:${seconds}`;
            } else {
                clock.innerHTML = `${hours}:${minutes}:${seconds}`;
            }
        }
    };

    const init_phase = get_phase();

    setInterval(update_function, 1000);
});
