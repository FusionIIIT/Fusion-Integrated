from types import SimpleNamespace as NS

import pytest

from modules.vms.domain import blacklist_match as bm


def probe(**kw):
    base = dict(name="", id_doc_number="", phone="", email="")
    return NS(**{**base, **kw})


def test_id_doc_normalised():
    assert bm.matches(probe(id_doc_number="ab 12 34"), probe(id_doc_number=" AB1234"))


def test_phone_digits_last_ten():
    assert bm.matches(probe(phone="98765 43210"), probe(phone="+91-9876543210"))
    assert not bm.matches(probe(phone="9876543210"), probe(phone="9876543211"))


def test_email_case_insensitive():
    assert bm.matches(probe(email="A@B.com"), probe(email=" a@b.COM "))


def test_name_alone_never_matches():
    assert not bm.matches(probe(name="John Doe"), probe(name="John Doe"))


def test_blank_fields_never_match():
    assert not bm.matches(probe(), probe())
    assert not bm.matches(probe(phone="abc"), probe(phone="xyz"))


def test_any_one_field_is_a_hit():
    e = probe(id_doc_number="X1", phone="1111111111", email="e@x.com")
    assert bm.matched_fields(e, probe(email="e@x.com", phone="2222222222")) == ["email"]
    assert bm.matched_fields(e, probe(id_doc_number="x1", email="e@x.com")) == [
        "id_doc_number", "email"]


def test_severity_ordering():
    assert [bm.severity_rank(s) for s in bm.SEVERITIES] == [0, 1, 2, 3]
    assert bm.max_severity(["low", "critical", "medium"]) == "critical"
    assert bm.max_severity([]) is None
    assert bm.severity_rank("HIGH") > bm.severity_rank("medium")
    with pytest.raises(ValueError):
        bm.severity_rank("nope")
