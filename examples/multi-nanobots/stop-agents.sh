#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
supervisorctl -c supervisord.conf shutdown
