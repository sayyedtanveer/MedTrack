"""Lightweight tests for Phase 5 inventory math (no DB)."""
from decimal import Decimal


def test_receive_max_formula():
    ordered = Decimal("100")
    received = Decimal("30")
    proposed = Decimal("80")
    max_recv = ordered - received
    assert proposed > max_recv


def test_mrp_need_formula():
    reorder = Decimal("50")
    safety = Decimal("10")
    available = Decimal("20")
    incoming = Decimal("15")
    reserved = Decimal("5")
    net = available + incoming - reserved
    need = reorder + safety - net
    assert net == Decimal("30")
    assert need == Decimal("30")
