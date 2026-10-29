"""Reference CLI programs used only by model-free tests, outside tool boundaries."""

SHOPPING = """import csv,json,sys
items={}
with open(sys.argv[1],encoding="utf-8",newline="") as f:
    for row in csv.DictReader(f):
        name=" ".join(row["item"].split()).casefold()
        if name: items[name]=items.get(name,0)+int(row["quantity"].strip() or "1")
print(json.dumps([{"item":k,"quantity":v} for k,v in sorted(items.items())],ensure_ascii=False))
"""
EXPENSE = """import csv,json,sys
from decimal import Decimal,ROUND_HALF_UP
sums={}
with open(sys.argv[1],encoding="utf-8",newline="") as f:
    for row in csv.DictReader(f):
        if row["status"].strip().casefold()!="paid": continue
        key=" ".join(row["category"].split()).casefold() or "uncategorized"
        value=Decimal(row["amount"]).quantize(Decimal(".01"),rounding=ROUND_HALF_UP)
        sums[key]=sums.get(key,Decimal(0))+value
print(json.dumps({"categories":[{"category":k,"total":format(v,".2f")} for k,v in sorted(sums.items())],"total":format(sum(sums.values(),Decimal(0)),".2f")},ensure_ascii=False))
"""
REMINDER = """import json,sys
from datetime import datetime,timezone
with open(sys.argv[1],encoding="utf-8") as f: data=json.load(f)
cutoff=datetime.fromisoformat(data["as_of"])
result=[]
for row in data["reminders"]:
    if row["completed"] or not row.get("due"): continue
    due=datetime.fromisoformat(row["due"])
    if due.tzinfo is not None and due<=cutoff:
        result.append((due,row["id"],{"id":row["id"],"title":row["title"],"due_utc":due.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}))
print(json.dumps([row for _,_,row in sorted(result)],ensure_ascii=False))
"""
REFERENCES = {
    "shopping-csv": SHOPPING,
    "expense-summary": EXPENSE,
    "reminder-repair": REMINDER,
}
