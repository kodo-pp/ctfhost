#!/usr/bin/env bash

set -e

if [[ -z "$1" || "$1" == "--help" ]]; then
    echo "Usage: $0 <username>"
    echo "Changes password for specified user in CTFHost database"
    exit 1
fi

username="$1"

printf "Checking if user '${username}' exists... "
if ! ./check-user.py "${username}"; then
    echo "No"
    echo "The specified user does not exist in the database"
    exit 1
fi
echo "Yes"

printf "Enter new CTFHost password for user '${username}': "
read -s password
echo
printf "Re-enter this password to confirm it: "
read -s password_confirmation
echo

if [[ "${password}" != "${password_confirmation}" ]]; then
    echo "Error: password and its confirmation do not match"
    exit 1
fi

printf "Updating password for user '${username}'... "
if ! echo "${password}" | ./update-password.py "${username}"; then
    echo "Failed"
    exit 1
fi
echo "Done"
exit 0
