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
