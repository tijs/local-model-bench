"""Exercise the versioned tasks with reference repairs and faulty starters."""

import sys
import unittest
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pi_coding.workspace import check
from run_pi_coding import SUITE
from test_pi_coding import REFERENCES as V1

REFERENCES = {
    "page-cursors": V1["page-cursors"],
    "batch-ledger": {
        "ledger.py": """from copy import deepcopy

def commit(state, batch):
    result = deepcopy(state)
    balances, seen = result['balances'], result['seen']
    for event, src, dst, amount in batch:
        details = [src, dst, amount]
        if src == dst or src not in balances or dst not in balances or type(amount) is not int or amount <= 0:
            raise ValueError('invalid')
        if event in seen:
            if seen[event] != details:
                raise ValueError('conflict')
            continue
        if amount > balances[src]:
            raise ValueError('funds')
        balances[src] -= amount
        balances[dst] += amount
        seen[event] = details
    return result
""",
        "recovery.py": """from ledger import commit

def restore(snapshot, batches):
    state = snapshot if isinstance(snapshot.get('balances'),dict) else {'balances':snapshot,'seen':{}}
    rejected = []
    for index, batch in enumerate(batches):
        try:
            state = commit(state, batch)
        except ValueError:
            rejected.append(index)
    return [state, rejected]
""",
    },
    "build-waves": {
        "planner.py": """from graphlib import TopologicalSorter, CycleError

def waves(graph, targets, changed, cached):
    scope = set()
    todo = list(targets)
    while todo:
        job = todo.pop()
        if job not in scope:
            scope.add(job)
            todo.extend(graph.get(job, []))
    missing = scope - graph.keys()
    if missing:
        raise ValueError('missing: ' + min(missing))
    try:
        order = list(TopologicalSorter({j: graph[j] for j in scope}).static_order())
    except CycleError:
        raise ValueError('cycle')
    levels, result = {}, []
    for job in order:
        level = max((levels[p] for p in graph[job]), default=0)
        if level or job in changed or job not in cached:
            level += 1
            if level > len(result):
                result.append([])
            result[level-1].append(job)
        levels[job] = level
    return [sorted(group) for group in result]
""",
    },
    "temporal-overlay": {
        "calendar_store.py": """def latest(records, asof):
    active = {}
    for key, rev, a, b, value in records:
        if rev <= asof and (key not in active or active[key][0] <= rev):
            active[key] = (rev, a, b, value)
    return active
""",
        "timeline.py": """from calendar_store import latest

def render(records, lo, hi, asof):
    active = [(max(lo,a),min(hi,b),-rev,k,v) for k,(rev,a,b,v) in latest(records,asof).items()
              if v is not None and max(a,lo)<min(b,hi)]
    points = sorted({p for a,b,*_ in active for p in (a,b)})
    result = []
    for a,b in zip(points,points[1:]):
        winners = [(r,k,v) for s,e,r,k,v in active if s<=a<e]
        if winners:
            value = min(winners)[2]
            if result and result[-1][1:] == [a,value]:
                result[-1][1] = b
            else:
                result.append([a,b,value])
    return result

def evaluate(records, windows):
    return [render(records,*window) for window in windows]
""",
    },
}


class HardCodingTests(unittest.TestCase):
    def test_grades(self):
        paths = list(SUITE.with_name("pi-coding-v2").glob("*.yaml"))
        self.assertEqual({p.stem for p in paths}, set(REFERENCES))
        for path in paths:
            with self.subTest(task=path.stem):
                task = yaml.safe_load(path.read_text())
                self.assertFalse(check(task, task["files"], hidden=True)["passed"])
                grade = check(task, task["files"] | REFERENCES[path.stem], hidden=True)
                self.assertTrue(grade["passed"], grade)

    def test_plausible_partial_repairs_fail_withheld_checks(self):
        mutations = {
            "batch-ledger": (
                "ledger.py",
                "result = deepcopy(state)",
                "result = state.copy()",
            ),
            "build-waves": (
                "planner.py",
                "order = list(TopologicalSorter",
                "if not changed and set(scope) <= set(cached): return []\n        order = list(TopologicalSorter",
            ),
            "temporal-overlay": (
                "calendar_store.py",
                "active[key][0] <= rev",
                "active[key][0] < rev",
            ),
        }
        for name, (file, correct, broken) in mutations.items():
            with self.subTest(task=name):
                task = yaml.safe_load(
                    (SUITE.with_name("pi-coding-v2") / (name + ".yaml")).read_text()
                )
                files = task["files"] | REFERENCES[name]
                self.assertIn(correct, files[file])
                files[file] = files[file].replace(correct, broken)
                self.assertTrue(check(task, files, hidden=False)["passed"])
                self.assertFalse(check(task, files, hidden=True)["passed"])
