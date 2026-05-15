from collections.abc import Callable
from typing import Any

import pytest

import justwatch


class FakeResponse:
    def __init__(self, payload: object) -> None:
        self.payload = payload

    def json(self) -> object:
        return self.payload

    def raise_for_status(self) -> None:
        return None


def test_get_amazon_prices_returns_amazon_buy_offers(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = _payload(
        [
            _offer("amazon_prime", "BUY", "UHD", 14.99, "USD"),
            _offer("amazon", "BUY", "HD", 9.99, "USD"),
        ]
    )
    calls: list[dict[str, Any]] = []
    monkeypatch.setattr(justwatch.requests, "post", _post_factory(FakeResponse(payload), calls))

    assert justwatch.get_amazon_prices(329865, "movie") == [
        {"quality": "UHD", "price": 14.99, "currency": "USD"},
        {"quality": "HD", "price": 9.99, "currency": "USD"},
    ]
    assert calls[0]["url"] == "https://apis.justwatch.com/graphql"
    assert calls[0]["json"]["variables"] == {
        "tmdbId": "329865",
        "contentTypes": ["MOVIE"],
    }


def test_get_amazon_prices_returns_empty_list_when_not_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, Any]] = []
    monkeypatch.setattr(
        justwatch.requests,
        "post",
        _post_factory(FakeResponse({"data": {"searchTitles": {"edges": []}}}), calls),
    )

    assert justwatch.get_amazon_prices(329865, "movie") == []


def test_get_amazon_prices_filters_out_non_amazon_offers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = _payload(
        [
            _offer("itunes", "BUY", "HD", 7.99, "USD"),
            _offer("amazon_prime", "RENT", "HD", 3.99, "USD"),
            _offer("amazon_prime", "BUY", "HD", 9.99, "USD"),
        ]
    )
    calls: list[dict[str, Any]] = []
    monkeypatch.setattr(justwatch.requests, "post", _post_factory(FakeResponse(payload), calls))

    assert justwatch.get_amazon_prices(329865, "movie") == [
        {"quality": "HD", "price": 9.99, "currency": "USD"}
    ]


def _post_factory(
    response: FakeResponse, calls: list[dict[str, Any]]
) -> Callable[..., FakeResponse]:
    def post(*_args: Any, **kwargs: Any) -> FakeResponse:  # noqa: ANN401
        calls.append({"url": _args[0], **kwargs})
        return response

    return post


def _payload(offers: list[dict[str, Any]]) -> dict[str, Any]:
    return {"data": {"searchTitles": {"edges": [{"node": {"offers": offers}}]}}}


def _offer(
    technical_name: str,
    monetization_type: str,
    presentation_type: str,
    retail_price: float,
    currency: str,
) -> dict[str, Any]:
    return {
        "monetizationType": monetization_type,
        "presentationType": presentation_type,
        "retailPrice": retail_price,
        "currency": currency,
        "package": {"technicalName": technical_name},
    }
