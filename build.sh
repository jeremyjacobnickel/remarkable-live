#!/bin/sh
# Baut rmgrab für den reMarkable Paper Pro (Linux, ARM64, statisch).
set -e
cd "$(dirname "$0")/rmgrab"
CGO_ENABLED=0 GOOS=linux GOARCH=arm64 go build -trimpath -ldflags='-s -w' -o rmgrab-linux-arm64 .
