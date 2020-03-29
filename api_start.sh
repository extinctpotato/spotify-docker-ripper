#!/bin/sh
uwsgi --ini /etc/sparrow.ini --plugin python3 --pidfile /tmp/sparrow.pid
supervisorctl start nginx
