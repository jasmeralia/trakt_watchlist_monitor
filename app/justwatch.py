from typing import Any

import requests

GRAPHQL_URL = "https://apis.justwatch.com/graphql"
AMAZON_PACKAGES = {"amazon", "amazon_prime"}

PriceOffer = dict[str, str | float]


def get_amazon_prices(tmdb_id: int, media_type: str) -> list[PriceOffer]:
    response = requests.post(
        GRAPHQL_URL,
        json={
            "query": _SEARCH_QUERY,
            "variables": {
                "tmdbId": str(tmdb_id),
                "contentTypes": [_content_type(media_type)],
            },
        },
        timeout=30,
    )
    response.raise_for_status()

    payload = response.json()
    if not isinstance(payload, dict):
        return []

    title = _first_title(payload)
    if title is None:
        return []

    offers = title.get("offers")
    if not isinstance(offers, list):
        return []

    return [
        price
        for offer in offers
        if isinstance(offer, dict)
        if (price := _amazon_buy_price(offer)) is not None
    ]


def _content_type(media_type: str) -> str:
    if media_type == "movie":
        return "MOVIE"
    if media_type == "show":
        return "SHOW"
    return media_type.upper()


def _first_title(payload: dict[Any, Any]) -> dict[Any, Any] | None:
    title: dict[Any, Any] | None = None
    data = payload.get("data")
    if isinstance(data, dict):
        search_titles = data.get("searchTitles")
        if isinstance(search_titles, dict):
            nodes = search_titles.get("nodes")
            if isinstance(nodes, list) and nodes and isinstance(nodes[0], dict):
                title = nodes[0]
            else:
                title = _first_edge_node(search_titles)
    return title


def _first_edge_node(search_titles: dict[Any, Any]) -> dict[Any, Any] | None:
    edges = search_titles.get("edges")
    if isinstance(edges, list) and edges and isinstance(edges[0], dict):
        node = edges[0].get("node")
        if isinstance(node, dict):
            return node
    return None


def _amazon_buy_price(offer: dict[Any, Any]) -> PriceOffer | None:
    if str(offer.get("monetizationType", "")).lower() != "buy":
        return None

    package = offer.get("package")
    if not isinstance(package, dict):
        return None

    technical_name = package.get("technicalName")
    if technical_name not in AMAZON_PACKAGES:
        return None

    quality = _quality(offer.get("presentationType"))
    price = offer.get("retailPrice")
    currency = offer.get("currency")
    if quality is None or not isinstance(price, int | float) or not isinstance(currency, str):
        return None

    return {"quality": quality, "price": float(price), "currency": currency}


def _quality(presentation_type: object) -> str | None:
    if not isinstance(presentation_type, str):
        return None

    normalized = presentation_type.upper()
    if normalized in {"4K", "UHD"}:
        return "UHD"
    if normalized in {"HD", "SD"}:
        return normalized
    return None


_SEARCH_QUERY = """
query SearchTitles($tmdbId: String!, $contentTypes: [ContentType!]) {
  searchTitles(
    externalIds: {tmdb: $tmdbId}
    filter: {contentTypes: $contentTypes}
    first: 1
  ) {
    edges {
      node {
        offers {
          monetizationType
          presentationType
          retailPrice
          currency
          package {
            technicalName
          }
        }
      }
    }
  }
}
"""
