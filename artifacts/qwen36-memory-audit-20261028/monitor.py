"""Read-only telemetry beside the unchanged protective supervisor."""
from __future__ import annotations

import datetime
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

root = Path(sys.argv[1])
runtime = Path(sys.argv[2])
root.mkdir(parents=True, exist_ok=True)
started = time.monotonic()
mapped = False
with (root / 'vm-and-status.jsonl').open('a', buffering=1) as log:
    while not (root / 'outcome.json').exists() and time.monotonic() - started < 4000:
        row = {'time': datetime.datetime.now(datetime.timezone.utc).isoformat()}
        for label, argv in [('vm_stat', ['vm_stat']), ('swap', ['sysctl', 'vm.swapusage'])]:
            row[label] = subprocess.run(argv, capture_output=True, text=True, timeout=3, check=False).stdout
        try:
            with urllib.request.urlopen('http://127.0.0.1:8024/v1/mei/status', timeout=0.75) as response:
                row['status'] = json.load(response)
            if not mapped and (runtime / 'server.pid').exists():
                pid = int((runtime / 'server.pid').read_text().strip())
                result = subprocess.run(['vmmap', '-summary', str(pid)], capture_output=True, text=True, timeout=10, check=False)
                (root / 'server-vmmap.txt').write_text(result.stdout + result.stderr)
                mapped = True
        except (OSError, ValueError, TimeoutError, subprocess.TimeoutExpired) as error:
            row['status_error'] = str(error)
        log.write(json.dumps(row) + '\n')
        time.sleep(1)
