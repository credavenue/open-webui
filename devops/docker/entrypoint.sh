#!/bin/bash

#echo "## :::> Starting Supervisor <:::"
#exec /usr/local/bin/supervisord -c /etc/supervisor/supervisord.conf
fluentd -c /etc/fluentd/fluent.conf -v
sleep 5
exec bash /app/backend/start.sh
