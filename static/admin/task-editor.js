function ActionError(text)
{
    this.message = text;
}


function make_http_request(address, data)
{
    let request = new XMLHttpRequest();
    request.open('POST', address, false);
    request.send(data);

    if (request.status !== 200) {
        throw new Error('Action page returned non-ok status');
    }

    let response = JSON.parse(request.responseText);
    if (response.success) {
        return response;
    } else {
        throw new Error(response.error_message);
    }
}


function open_task_editor(task_id, text, title, value, labels)
{
    let overlay = document.querySelector('#task-editor-overlay');
    if (overlay === null) {
        throw new Error('There is no task editor overlay element on the page');
    }
    
    if (overlay.classList.contains('task-editor-active')) {
        throw new Error('Another task editor is already active');
    }
    
    overlay.classList.add('task-editor-active');

    let in_taskid   = document.querySelector('#task-editor-overlay #task-editor-taskid-input');
    let in_title    = document.querySelector('#task-editor-overlay #task-editor-title-input');
    let in_value    = document.querySelector('#task-editor-overlay #task-editor-value-input');
    let in_text     = document.querySelector('#task-editor-overlay #task-editor-text-input');
    let in_labels   = document.querySelector('#task-editor-overlay #task-editor-labels-input');

    in_taskid.value   = task_id;
    in_title.value    = title;
    in_value.value    = value;
    in_text.value     = text;
    in_labels.value   = labels.join(' ');
    
    let submit_button = document.querySelector('#task-editor-overlay #task-editor-submit-button');
    let cancel_button = document.querySelector('#task-editor-overlay #task-editor-cancel-button');

    submit_button.addEventListener('click', run_task_editor_submit);
    cancel_button.addEventListener('click', run_task_editor_cancel);
}


function close_task_editor()
{
    let overlay = document.querySelector('#task-editor-overlay');
    if (!overlay.classList.contains('task-editor-active')) {
        throw new Error('Task editor is not yet open');
    }

    let submit_button = document.querySelector('#task-editor-overlay #task-editor-submit-button');
    let cancel_button = document.querySelector('#task-editor-overlay #task-editor-cancel-button');
    submit_button.removeEventListener('click', run_task_editor_submit);
    cancel_button.removeEventListener('click', run_task_editor_cancel);

    overlay.classList.remove('task-editor-active');
}


function run_task_editor_submit()
{
    setTimeout(function() {
        try {
            task_editor_submit();
        } catch (e) {
            error_message(e.message);
        }
    }, 0);
}


function run_task_editor_cancel()
{
    setTimeout(function() {
        try {
            task_editor_cancel();
        } catch (e) {
            error_message(e.message);
        }
    }, 0);
}


function task_editor_submit()
{
    let task_id   = document.querySelector('#task-editor-overlay #task-editor-taskid-input').value;
    let text      = document.querySelector('#task-editor-overlay #task-editor-text-input').value;
    let title     = document.querySelector('#task-editor-overlay #task-editor-title-input').value;
    let labels_s  = document.querySelector('#task-editor-overlay #task-editor-labels-input').value;
    let labels    = labels_s.split(' ').filter(Boolean);
    let value     = parseInt(document.querySelector('#task-editor-overlay #task-editor-value-input').value);

    let data = JSON.stringify({
        'task_id': task_id,
        'text': text,
        'title': title,
        'value': value,
        'labels': labels,
    });

    let response;
    try {
        response = make_http_request('/api/add_or_update_task', data);
    } catch (e) {
        if (e instanceof ActionError) {
            error_message(e.message);
            return;
        } else {
            throw e;
        }
    }
    
    // Task submitted successfully, close the editor
    close_task_editor();
    
    // Reload the page
    location.reload();
}


function task_editor_cancel()
{
    // TODO: maybe ask for user confirmation
    close_task_editor();
}
