function ActionError(text)
{
    this.message = text;
}


function open_task_editor(task_id, text, title, value, labels, loaded_flags, group, order)
{
    let overlay = document.querySelector('#task-editor-overlay');
    if (overlay === null) {
        throw new Error('There is no task editor overlay element on the page');
    }
    
    if (overlay.classList.contains('task-editor-active')) {
        throw new Error('Another task editor is already active');
    }

    let container = document.getElementById('task-editor-flags');
    container.innerHTML = '';
    flags = {};
    flagno = 0;
    
    overlay.classList.add('task-editor-active');

    let in_taskid   = document.querySelector('#task-editor-overlay #task-editor-taskid-input');
    let in_title    = document.querySelector('#task-editor-overlay #task-editor-title-input');
    let in_value    = document.querySelector('#task-editor-overlay #task-editor-value-input');
    let in_text     = document.querySelector('#task-editor-overlay #task-editor-text-input');
    let in_labels   = document.querySelector('#task-editor-overlay #task-editor-labels-input');
    let in_group    = document.querySelector('#task-editor-overlay #task-editor-groupname-input');
    let in_order    = document.querySelector('#task-editor-overlay #task-editor-order-input');

    in_taskid.value = task_id;
    in_title.value  = title;
    in_value.value  = value;
    in_text.value   = text;
    in_labels.value = labels.join(' ');
    in_group.value  = group;
    in_order.value  = order;
    
    let submit_button = document.querySelector('#task-editor-overlay #task-editor-submit-button');
    let cancel_button = document.querySelector('#task-editor-overlay #task-editor-cancel-button');

    submit_button.addEventListener('click', run_task_editor_submit);
    cancel_button.addEventListener('click', run_task_editor_cancel);

    for (let flag of loaded_flags) {
        let no = flagno;
        add_flag();
        flags[no] = flag;
    }
    update_flags_ui();
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
    let group     = parseInt(document.querySelector('#task-editor-overlay #task-editor-groupname-input').value);
    let order     = parseInt(document.querySelector('#task-editor-overlay #task-editor-order-input').value);
    /* global flags */

    let flaglist = [];
    for (let no in flags) {
        flaglist.push(flags[no]);
    }

    let data = JSON.stringify({
        'task_id': task_id,
        'text': text,
        'title': title,
        'value': value,
        'labels': labels,
        'flags': flaglist,
        'group': group,
        'order': order
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



var flags = {};
var flagno = 0;


function add_flag()
{
    const flag_input_template = `
    <div class="w3-row-padding" id="flag##no##">
        <div class="w3-col s4 m4 l4">
            <select id="flag_type##no##" onchange="update_flagtype_internal(##no##)" class="w3-input w3-border">
                <option value="string">${locale_messages['flagtype_string']}</option>
                <option value="regex">${locale_messages['flagtype_regex']}</option>
                <option value="program">${locale_messages['flagtype_program']}</option>
            </select>
        </div>
        <div class="w3-col s6 m6 l6">
            <input id="flag_data##no##"
                   type="text"
                   class="w3-input w3-border"
                   onchange="update_flagdata_internal(##no##)"
                   style="font-family: monospace;">
        </div>
        <div class="w3-col s2 m2 l2">
            <a class="w3-button w3-red" href="javascript:delete_flag(##no##)">${locale_messages['delete_flag']}</a>
        </div>
    </div>
    `
    let container = document.getElementById('task-editor-flags');
    
    // Ugly, I know...
    container.innerHTML += flag_input_template.split('##no##').join(flagno.toString());

    let select_element = document.getElementById(`flag_type${flagno}`);
    select_element.value = 'string';
    flags[flagno] = {'type': 'string', 'data': ''};
    ++flagno;

    // Костыль № 9247
    update_flags_ui();
}


function update_flags_ui()
{
    for (let no in flags) {
        update_flag_ui(no);
    }
}


function update_flag_ui(no)
{
    let in_type = document.getElementById(`flag_type${no}`);
    let in_data = document.getElementById(`flag_data${no}`);
    in_type.value = flags[no].type;
    in_data.value = flags[no].data;
}


function update_flagtype_internal(no)
{
    let select_element = document.getElementById(`flag_type${no}`);
    let text = select_element.options[select_element.selectedIndex].value;
    flags[no].type = text;
}


function update_flagdata_internal(no)
{
    let input_element = document.getElementById(`flag_data${no}`);
    let text = input_element.value;
    flags[no].data = text;
}


function delete_flag(no)
{
    let flag_container = document.getElementById(`flag${no}`);
    flag_container.remove();
    delete flags[no];
}


function task_editor_cancel()
{
    // TODO: maybe ask for user confirmation
    close_task_editor();
}
