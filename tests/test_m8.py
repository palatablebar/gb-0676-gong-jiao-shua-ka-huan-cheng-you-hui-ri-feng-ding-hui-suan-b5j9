from app.modules.m8_settlement.rules import evaluate
from app.errors import DomainError
import pytest
def test_real_sample_archive_ready(result): assert result["stages"][7]["metrics"]["ready"] is True
def test_real_sample_archive_source_count(result): assert result["stages"][7]["metrics"]["source_lines"]==result["stages"][6]["metrics"]["accepted_inputs"]
def test_real_sample_seal_stable(result):
    rows=result["stages"][6]["rows"];assert evaluate(rows,{})["metrics"]["sha256"]==evaluate(rows,{})["metrics"]["sha256"]
def test_unbalanced_blocked():
    with pytest.raises(DomainError) as e:evaluate([],{"reconcile":{"metrics":{"balanced":False}}})
    assert e.value.code=="UNBALANCED"
def test_funding_unbalanced_blocked():
    "资金确认未对平前不封存日结"
    with pytest.raises(DomainError) as e:evaluate([],{"funding":{"metrics":{"balanced":False}}})
    assert e.value.code=="FUNDING_UNBALANCED"
def test_funding_balanced_seals_with_totals():
    r=evaluate([],{"funding":{"metrics":{"balanced":True,"transfer_confirmed":"1.00","cap_confirmed":"2.00","subsidy_total":"3.00"}}})
    assert r["metrics"]["funding_subsidy"]=="3.00" and r["metrics"]["funding_balanced"] is True
def test_duplicate_archive_key():
    with pytest.raises(DomainError):evaluate([{"event_id":"1"},{"event_id":"1"}],{})
def test_real_sample_manifest_has_hash(result): assert len(result["manifest"]["input_sha256"])==64
def test_real_sample_export_rows_match(result): assert result["stages"][7]["rows"]==result["stages"][6]["rows"]
def test_real_sample_seal_carries_funding(result):
    m=result["stages"][7]["metrics"]
    assert m["funding_transfer"]=="16.00" and m["funding_cap"]=="16.00" and m["funding_subsidy"]=="32.00"
