"""Pass every frozen external oracle with a reference, and reject every starter."""

import sys
import tempfile
import time
import unittest
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pi_coding.workspace import TaskWorkspace, check
from run_pi_coding import SUITE

REFERENCES = {
    "merge-ranges": {
        "ranges.py": """def merge_ranges(items):
    out = []
    for a,b in sorted(items):
        if out and a <= out[-1][1]+1:
            out[-1] = out[-1][0], max(b, out[-1][1])
        else: out.append((a,b))
    return out
"""
    },
    "event-keys": {
        "keys.py": "def event_key(x): return x.strip().casefold()",
        "events.py": """from keys import event_key
def unique_events(values):
    d = {}
    for v in values:
        if event_key(v): d.setdefault(event_key(v),v)
    return list(d.values())
""",
    },
    "unicode-stream": {
        "stream.py": "def decode_chunks(chunks): return b''.join(chunks).decode()"
    },
    "config-option": {
        "config.py": """def load_config(raw):
    n=raw.get("attempts",3)
    if type(n) is not int or not 1<=n<=8: raise ValueError()
    return dict(raw,attempts=n)
""",
        "worker.py": 'from config import load_config\ndef retry_indices(raw):return list(range(1,1+load_config(raw)["attempts"]))',
    },
    "resume-import": {
        "ingest.py": """def resume(saved,incoming,limit=None):
    out=list(saved)
    seen={x["id"] for x in saved}
    for r in incoming:
        if r["id"] not in seen and (limit is None or len(out)-len(saved)<limit):
            seen.add(r["id"]);out.append(r)
    return out
"""
    },
    "midnight-window": {
        "hours.py": "def active(t,s,e): return s<=t<e if s<=e else t>=s or t<e"
    },
    "page-cursors": {
        "store.py": "def page(items,cursor,size):\n    a=cursor or 0\n    return items[a:a+size], a+size if a+size<len(items) else None",
        "client.py": """from store import page
def collect(items,size):
    result=[];cursor=None
    while True:
        batch,cursor=page(items,cursor,size);result.extend(batch)
        if cursor is None:return result
""",
    },
    "ledger-rounding": {
        "money.py": "from decimal import Decimal,ROUND_HALF_UP\ndef cents(t):return int((Decimal(t)*100).quantize(Decimal(1),rounding=ROUND_HALF_UP))",
        "ledger.py": """from money import cents
def totals(rows):
    d={}
    for r in rows:
        if r["status"]=="posted":d[r["account"]]=d.get(r["account"],0)+cents(r["amount"])
    return d
""",
    },
    "proverb": {
        "proverb.py": """def proverb(*items,qualifier=None):
    if not items:return []
    first=(qualifier+' ' if qualifier else '')+items[0]
    return [f"For want of a {a} the {b} was lost." for a,b in zip(items,items[1:])]+[f"And all for the want of a {first}."]
"""
    },
    "transpose": {
        "transpose.py": """def transpose(text):
    rows=text.split('\u005cn')
    return '\u005cn'.join(''.join(row[i] if len(row)>i else ' ' for row in rows[:max(j for j,r in enumerate(rows) if len(r)>i)+1]) for i in range(max(map(len,rows))))
""".replace("'\n'", "'\\n'")
    },
    "affine-cipher": {
        "affine_cipher.py": """from math import gcd
def transform(text,a,b,dec):
    if gcd(a,26)!=1: raise ValueError("a and m must be coprime.")
    return ''.join(c if c.isdigit() else chr(97+(((ord(c)-97-b)*pow(a,-1,26)) if dec else a*(ord(c)-97)+b)%26) for c in text.lower() if c.isascii() and c.isalnum())
def encode(text,a,b):
    s=transform(text,a,b,False)
    return ' '.join(s[i:i+5] for i in range(0,len(s),5))
def decode(text,a,b):return transform(text,a,b,True)
"""
    },
    "variable-length-quantity": {
        "variable_length_quantity.py": """def encode(nums):
    out=[]
    for n in nums:
        parts=[n&127];n>>=7
        while n:parts.append(128+(n&127));n>>=7
        out.extend(reversed(parts))
    return out
def decode(data):
    out=[];n=0
    for byte in data:
        n=(n<<7)+(byte&127)
        if byte<128:out.append(n);n=0
    if data and data[-1]>=128:raise ValueError("incomplete sequence")
    return out
"""
    },
}


class CodingTests(unittest.TestCase):
    def test_oracles(self):
        self.assertEqual({p.stem for p in SUITE.glob("*.yaml")}, set(REFERENCES))
        for path in SUITE.glob("*.yaml"):
            with self.subTest(task=path.stem):
                task = yaml.safe_load(path.read_text())
                self.assertFalse(check(task, task["files"], hidden=True)["passed"])
                grades = check(task, REFERENCES[path.stem], hidden=True)
                self.assertTrue(grades["passed"], grades)

    def test_scoped_tools_and_transient_write(self):
        task = yaml.safe_load((SUITE / "event-keys.yaml").read_text())
        with tempfile.TemporaryDirectory() as root:
            w = TaskWorkspace(task, Path(root), time.monotonic(), 4096, 16384)
            self.assertIn("error", w.apply("read_file", {"path": "../oracle"}))
            req = {"path": "keys.py", "content": "new"}
            self.assertIn("error", w.apply("write_file", req))
            self.assertTrue(w.apply("write_file", req)["ok"])
            self.assertEqual(len(w.snapshots), 1)
