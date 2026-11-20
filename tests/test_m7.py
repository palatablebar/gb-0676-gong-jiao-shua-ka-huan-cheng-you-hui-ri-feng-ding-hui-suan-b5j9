from app.modules.m7_clearing.rules import evaluate
from decimal import Decimal
def test_real_sample_four_books(result): assert result["stages"][6]["metrics"]["balanced"] is True
def test_real_sample_final_lineage(result):
    m=result["stages"][6]["metrics"];assert m["accepted_inputs"]+m["quarantine_inputs"]+m["excluded"]==m["input"]
def test_real_sample_difference_is_explicit(result):
    rows=result["stages"][6]["rows"];assert any(r["status"]=="差异" for r in rows)
def test_real_sample_totals_exact(result):
    rows=result["stages"][6]["rows"];m=result["stages"][6]["metrics"]
    assert sum((Decimal(r["difference"]) for r in rows),Decimal(0))==Decimal(m["expected_total"])-Decimal(m["reported_total"])
def test_empty_reconcile():
    r=evaluate([],{});assert r["metrics"]["balanced"] is True and r["metrics"]["expected_total"]=="0"
def test_overlap_is_rejected():
    import pytest
    from app.errors import DomainError
    with pytest.raises(DomainError):evaluate([{"_line":1}],{"quarantine":[{"_line":1}]})
def test_real_sample_rejected_have_reason(result):
    assert all(r["reason"] and r["detail"] for r in result["stages"][6]["cumulative_quarantine"])
def test_real_sample_funding_crosscheck(result):
    m=result["stages"][6]["metrics"]
    assert m["funding_balanced"] is True and m["funding_transfer"]=="16.00" and m["funding_cap"]=="16.00"
def test_funding_mismatch_rejected():
    import pytest
    from app.errors import DomainError
    with pytest.raises(DomainError) as e:evaluate([],{"funding":{"metrics":{"expected_total":"9.99"}}})
    assert e.value.code=="FUNDING_MISMATCH"
def test_funding_matched_passes():
    r=evaluate([],{"funding":{"metrics":{"expected_total":"0.00","transfer_confirmed":"0.00","cap_confirmed":"0.00","balanced":True}}})
    assert r["metrics"]["funding_balanced"] is True
