#!/bin/bash

echo "## :::> Starting Supervisor <:::"
exec /usr/local/bin/supervisord -c /etc/supervisor/supervisord.conf