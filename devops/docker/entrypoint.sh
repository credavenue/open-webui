#!/bin/bash

echo "## :::> Starting Supervisor <:::"
exec /usr/bin/supervisord -c /etc/supervisor/supervisord.conf