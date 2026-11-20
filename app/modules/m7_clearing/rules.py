from decimal import Decimal
from app.reasons import sources
from app.errors import DomainError
from app.values import number
def evaluate(rows,context):
    intake=context.get("intake")
    bad=context.get("quarantine",[])
    accepted=set(x for row in rows for x in sources(row))
    rejected=set(x for row in bad for x in sources(row))
    if accepted & rejected: raise DomainError("LINEAGE_OVERLAP","同一来源行被重复裁决")
    m={"accepted_inputs":len(accepted),"quarantine_inputs":len(rejected),"output_records":len(rows)}
    if intake:
        excluded=intake["duplicate"]+intake["blank"]+intake["repeated_headers"]
        m.update(input=intake["input"],excluded=excluded,balanced=intake["input"]==len(accepted)+len(rejected)+excluded)
    else:m.update(input=len(accepted)+len(rejected),excluded=0,balanced=True)
    output=[]
    for row in rows:
        expected=Decimal(str(row.get("expected","0")));reported=Decimal(str(row.get("reported","0")))
        output.append({**row,"difference":str(expected-reported),"status":"通过" if expected==reported else "差异"})
    m.update(expected_total=str(sum((Decimal(str(r.get("expected","0"))) for r in rows),Decimal(0))),reported_total=str(sum((Decimal(str(r.get("reported","0"))) for r in rows),Decimal(0))),differences=sum(r["status"]=="差异" for r in output))
    funding=context.get("funding")
    if funding:
        fm=funding.get("metrics",{})
        if "expected_total" in fm and number(fm["expected_total"])!=number(m["expected_total"]): raise DomainError("FUNDING_MISMATCH","资金确认与清分应扣不一致")
        m.update(funding_transfer=fm.get("transfer_confirmed"),funding_cap=fm.get("cap_confirmed"),funding_balanced=fm.get("balanced"))
    return {"rows":output,"quarantine":[],"metrics":m}
