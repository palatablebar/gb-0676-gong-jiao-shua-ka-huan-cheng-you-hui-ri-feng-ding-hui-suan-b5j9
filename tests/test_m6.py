from app.modules.m5_discounts.rules import evaluate as discount
from app.modules.m6_funding.rules import evaluate as funding
from app.errors import DomainError
from decimal import Decimal
import pytest
def ride(id,minute,route="01",reported="2.50",day="2026-11-16",card="0001"):
    return {"event_id":f"e{id}","card":card,"business_day":day,"at":f"2026-11-16T{8+minute//60:02d}:{minute%60:02d}:00+00:00","route":route,"base_fare":"2.50","reported":reported,"fare_version":"F2","_sources":[id]}
def run(rides,context=None):
    context=context or {}
    return funding(discount(rides,context)["rows"],context)
def test_double_trigger_split_no_double_count():
    "TRAP-27 同一行程换乘与封顶同时触发，两类资金按各自份额确认"
    r=run([ride(1,0),ride(2,10,"02"),ride(3,20,"03"),ride(4,30,"01")])
    row=r["rows"][3]
    assert row["transfer_confirm"]=="1.00" and row["cap_confirm"]=="1.00" and row["expected"]=="0.50"
    assert Decimal(row["base_fare"])==Decimal(row["expected"])+Decimal(row["transfer_confirm"])+Decimal(row["cap_confirm"])
    m=r["metrics"]
    assert m["transfer_confirmed"]=="3.00" and m["cap_confirmed"]=="1.00" and m["subsidy_total"]=="4.00"
    assert m["subsidy_total"]!=m["cap_confirmed"] and m["double_trigger_trips"]==1
    assert Decimal(m["base_total"])==Decimal(m["expected_total"])+Decimal(m["subsidy_total"])
def test_ledger_unique_per_card_day():
    r=run([ride(1,0),ride(2,10,"02"),ride(3,0,day="2026-11-17")])
    assert r["metrics"]["ledger_rows"]==2
    assert sorted(l["ledger_id"] for l in r["ledger"])==["0001@2026-11-16","0001@2026-11-17"]
    same=run([ride(1,0),ride(2,10,"02")])
    assert same["metrics"]["ledger_rows"]==1 and same["ledger"][0]["trips"]==2
def test_ledger_conservation_and_status():
    r=run([ride(1,0),ride(2,10,"02")])
    line=r["ledger"][0]
    assert line["status"]=="对平" and line["conserved"]=="是"
    assert Decimal(line["base_total"])==Decimal(line["expected_total"])+Decimal(line["transfer_confirm"])+Decimal(line["cap_confirm"])
    assert r["metrics"]["balanced"] is True and r["metrics"]["unbalanced_rows"]==0
def test_adjustment_basis_records_double_trip():
    r=run([ride(1,0),ride(2,10,"02"),ride(3,20,"03"),ride(4,30,"01")])
    line=r["ledger"][0]
    assert "先换乘" in line["adjustment"] and "双优惠行程1条（e4）" in line["adjustment"]
    assert r["rows"][3]["funding_basis"].startswith("双优惠分账")
def test_ledger_keeps_sources_and_fares():
    r=run([ride(1,0),ride(2,10,"02")])
    line=r["ledger"][0]
    assert line["_sources"]==[1,2] and line["fare_detail"]=="F2:2.50×2"
def test_input_order_invariant():
    rows=[ride(1,0),ride(2,10,"02"),ride(3,20,"03"),ride(4,30,"01")]
    assert run(rows)["ledger"]==run(list(reversed(rows)))["ledger"]
def test_split_broken_flagged_not_sealed():
    bad={"event_id":"x1","card":"0001","business_day":"2026-11-16","at":"2026-11-16T08:00:00+00:00","route":"01","base_fare":"2.50","transfer_discount":"1.00","cap_discount":"1.00","expected":"1.00","reported":"2.50","_sources":[9]}
    r=funding([bad],{})
    assert r["ledger"][0]["status"]=="失衡" and r["metrics"]["balanced"] is False and r["metrics"]["unbalanced_rows"]==1
def test_negative_parameter_rejected():
    with pytest.raises(DomainError):funding([],{"parameters":{"daily_cap":"-1"}})
def test_unreadable_parameter_rejected():
    with pytest.raises(DomainError):funding([],{"parameters":{"daily_cap":"abc"}})
def test_empty_ledger_balanced():
    r=funding([],{})
    assert r["ledger"]==[] and r["metrics"]["balanced"] is True and r["metrics"]["subsidy_total"]=="0.00"
def test_real_sample_ledger(result):
    m=result["stages"][5]["metrics"]
    assert m["ledger_rows"]==8 and m["balanced"] is True
    assert m["base_total"]=="80.00" and m["expected_total"]=="48.00"
    assert m["transfer_confirmed"]=="16.00" and m["cap_confirmed"]=="16.00" and m["subsidy_total"]=="32.00"
    assert Decimal(m["base_total"])==Decimal(m["expected_total"])+Decimal(m["subsidy_total"])
def test_real_sample_ledger_covers_sources(result):
    ledger=result["stages"][5]["ledger"]
    covered={s for line in ledger for s in line["_sources"]}
    assert len(covered)==result["stages"][6]["metrics"]["accepted_inputs"]
    assert all(line["status"]=="对平" for line in ledger)
