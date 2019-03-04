#!/usr/bin/env bash

set -e

if [[ -z "$1" || "$1" == "--help" ]]; then
    echo "Usage: $0 <lang_code>"
    echo "Example: $0 ru"
    echo "Downloads and saves the specified locale for Flatpickr"
    exit 1
fi

wget "https://npmcdn.com/flatpickr/dist/l10n/$1.js" -O "static/flatpickr/locale/$1.js"

echo "Success"
