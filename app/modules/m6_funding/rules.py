from decimal import Decimal
from app.values import number,money,instant
from app.errors import DomainError
def parameters(context):
    params=context.get("parameters",{})
    cap=number(params.get("daily_cap","6.00"));off=number(params.get("transfer_discount","1.00"));window=number(params.get("transfer_minutes","60"))
    if cap<0 or off<0 or window<0:raise DomainError("BAD_DISCOUNT","优惠参数不能为负")
    return cap,off,window
def evaluate(rows,context):
    cap,off,window=parameters(context)
    trips=sorted(rows,key=lambda r:(r["card"],r["business_day"],instant(r["at"]),r["event_id"]))
    enriched=[];groups={}
    for row in trips:
        base=number(row["base_fare"]);transfer=number(row["transfer_discount"]);capd=number(row["cap_discount"]);expected=number(row["expected"])
        conserved=base==transfer+capd+expected
        if transfer>0 and capd>0:basis=f"双优惠分账：换乘确认{money(transfer)}、封顶确认{money(capd)}，同一差额不重复确认"
        elif transfer>0:basis="换乘减免确认"
        elif capd>0:basis="日封顶减免确认"
        else:basis="无优惠全额扣费"
        item={**row,"transfer_confirm":money(transfer),"cap_confirm":money(capd),"split_conserved":"是" if conserved else "否","funding_basis":basis}
        enriched.append(item);groups.setdefault((row["card"],row["business_day"]),[]).append(item)
    ledger=[]
    for (card,day),items in sorted(groups.items()):
        base_total=sum((number(i["base_fare"]) for i in items),Decimal(0))
        expected_total=sum((number(i["expected"]) for i in items),Decimal(0))
        reported_total=sum((number(i["reported"]) for i in items),Decimal(0))
        transfer_total=sum((number(i["transfer_confirm"]) for i in items),Decimal(0))
        cap_total=sum((number(i["cap_confirm"]) for i in items),Decimal(0))
        double=[i["event_id"] for i in items if number(i["transfer_confirm"])>0 and number(i["cap_confirm"])>0]
        conserved=base_total==expected_total+transfer_total+cap_total and all(i["split_conserved"]=="是" for i in items)
        fares={}
        for i in items:
            key=(i.get("fare_version","—"),i["base_fare"]);fares[key]=fares.get(key,0)+1
        fare_detail="、".join(f"{version}:{amount}×{count}" for (version,amount),count in sorted(fares.items()))
        adjustment=(f"先换乘减免（{money(off)}元/{window}分钟窗）后日封顶（{money(cap)}元）；"
                    f"换乘确认{money(transfer_total)}、封顶确认{money(cap_total)}，合计{money(transfer_total+cap_total)}=原价{money(base_total)}-实扣{money(expected_total)}")
        if double:adjustment+=f"；双优惠行程{len(double)}条（{'、'.join(double)}）按各自份额分账"
        ledger.append({"ledger_id":f"{card}@{day}","card":card,"business_day":day,"trips":len(items),
            "events":"、".join(i["event_id"] for i in items),
            "base_total":money(base_total),"expected_total":money(expected_total),"reported_total":money(reported_total),
            "difference":money(expected_total-reported_total),
            "transfer_confirm":money(transfer_total),"cap_confirm":money(cap_total),"subsidy_total":money(transfer_total+cap_total),
            "fare_detail":fare_detail,"double_trips":len(double),"adjustment":adjustment,
            "conserved":"是" if conserved else "否","status":"对平" if conserved else "失衡",
            "_sources":sorted({s for i in items for s in i.get("_sources",[])})})
    totals=lambda field:sum((number(l[field]) for l in ledger),Decimal(0))
    unbalanced=sum(l["status"]!="对平" for l in ledger)
    covered=sum(l["trips"] for l in ledger)
    metrics={"ledger_rows":len(ledger),"trips":len(enriched),
        "base_total":money(totals("base_total")),"expected_total":money(totals("expected_total")),"reported_total":money(totals("reported_total")),
        "transfer_confirmed":money(totals("transfer_confirm")),"cap_confirmed":money(totals("cap_confirm")),"subsidy_total":money(totals("subsidy_total")),
        "double_trigger_trips":sum(l["double_trips"] for l in ledger),"unbalanced_rows":unbalanced,
        "balanced":unbalanced==0 and covered==len(enriched)}
    return {"rows":enriched,"ledger":ledger,"quarantine":[],"metrics":metrics}
