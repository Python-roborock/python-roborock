"""Tests for Hawk request signing."""

from roborock import UserData
from roborock.web_api import _hawk
from roborock.web_api._hawk import _compact_json, _get_hawk_authentication
from tests.mock_data import USER_DATA


def test_hawk_authentication_signs_body(monkeypatch) -> None:
    """Body-bearing writes sign md5(compact JSON body) in the Hawk payload slot; GET is unchanged."""
    monkeypatch.setattr(_hawk.time, "time", lambda: 1_700_000_000)
    monkeypatch.setattr(_hawk.secrets, "token_urlsafe", lambda n: "fixednonce")
    rriot = UserData.from_dict(USER_DATA).rriot
    assert rriot is not None

    body = {"b": 2, "a": 1}
    signed = _get_hawk_authentication(rriot, "/p", body=body)
    unsigned = _get_hawk_authentication(rriot, "/p")
    formdata_signed = _get_hawk_authentication(rriot, "/p", formdata=body)

    assert signed != unsigned  # the body is actually covered by the MAC
    assert signed != formdata_signed  # body-signing differs from formdata-signing
    assert _compact_json(body) == '{"b":2,"a":1}'
