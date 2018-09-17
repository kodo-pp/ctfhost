#!/usr/bin/env bash
set -e
sh3 build
echo
echo "=== Running ==="
echo
./main "$@"
