"""merge a JSON object {asset: {field: value}} read from stdin into tools/notes.json 'assets' (python3 -I notes_set.py < x.json)"""
import json, os, sys
p = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'notes.json'); n = json.load(open(p))
for k, v in json.load(sys.stdin).items():
    if k.startswith('@'):
        n[k[1:]] = v
    else:
        n['assets'][k] = v
json.dump(n, open(p, 'w'), indent=1)
