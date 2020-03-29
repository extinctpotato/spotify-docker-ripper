#!/bin/sh

kill -s HUP $(cat /tmp/sparrow.pid)
