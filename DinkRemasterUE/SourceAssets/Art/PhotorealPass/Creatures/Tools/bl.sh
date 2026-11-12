#!/bin/bash
# Serialises this stream's Blender batch jobs (one process at a time, 4 threads). usage: bl.sh script.py -- args
cd "$(dirname "$0")"
exec flock "$(dirname "$0")/.blender.lock" env ALSOFT_DRIVERS=null blender -b -t 4 --python "$@"
