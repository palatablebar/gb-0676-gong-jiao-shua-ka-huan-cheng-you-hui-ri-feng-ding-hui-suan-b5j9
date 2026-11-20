import hashlib,json
from decimal import Decimal
from app.errors import DomainError
from app.reasons import sources
def evaluate(rows,context):
    funding=context.get("funding")
    if funding and not funding.get("metrics",{}).get("balanced",False): raise DomainError("FUNDING_UNBALANCED","资金确认未对平，不能封存日结")
    stages=[v for v in context.values() if isinstance(v,dict) and "metrics" in v]
    balances=[s["metrics"]["balanced"] for s in stages if "balanced" in s["metrics"]]
    if balances and not all(balances): raise DomainError("UNBALANCED","来源行未对平，不能归档")
    ids=[str(r.get("event_id",r.get("_line",""))) for r in rows]
    if len(ids)!=len(set(ids)): raise DomainError("ARCHIVE_DUPLICATE","归档业务键重复")
    encoded=json.dumps(rows,ensure_ascii=False,sort_keys=True,default=str).encode()
    metrics={"records":len(rows),"source_lines":len(set(x for row in rows for x in sources(row))),"sha256":hashlib.sha256(encoded).hexdigest(),"ready":True,"differences":sum(r.get("status")=="差异" for r in rows)}
    if funding:
        fm=funding["metrics"];metrics.update(funding_transfer=fm.get("transfer_confirmed"),funding_cap=fm.get("cap_confirmed"),funding_subsidy=fm.get("subsidy_total"),funding_balanced=True)
    return {"rows":rows,"quarantine":[],"metrics":metrics}
