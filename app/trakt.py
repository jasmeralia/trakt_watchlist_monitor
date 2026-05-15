from typing import Any

import requests

from config import settings

BASE_URL = "https://api.trakt.tv"


def refresh_token() -> None:
    response = requests.post(
        f"{BASE_URL}/oauth/token",
        json={
            "refresh_token": settings.trakt_refresh_token,
            "client_id": settings.trakt_client_id,
            "client_secret": settings.trakt_client_secret,
            "redirect_uri": "urn:ietf:wg:oauth:2.0:oob",
            "grant_type": "refresh_token",
        },
        headers=_headers(),
        timeout=30,
    )
    response.raise_for_status()
    token_data = response.json()
    settings.trakt_access_token = str(token_data["access_token"])
    settings.trakt_refresh_token = str(token_data["refresh_token"])


def get_watchlist() -> list[dict[str, Any]]:
    return _get(f"/users/{settings.trakt_username}/watchlist")


def get_collection() -> list[dict[str, Any]]:
    movies = _get(f"/users/{settings.trakt_username}/collection/movies")
    shows = _get(f"/users/{settings.trakt_username}/collection/shows")
    return [*movies, *shows]


def get_effective_watchlist() -> list[dict[str, Any]]:
    collection_ids = {_item_trakt_id(item) for item in get_collection()}
    return [
        normalized
        for item in get_watchlist()
        if (normalized := _normalize_watchlist_item(item)) is not None
        and normalized["trakt_id"] not in collection_ids
    ]


def _get(path: str) -> list[dict[str, Any]]:
    response = _request_with_refresh("GET", path)
    data = response.json()
    if not isinstance(data, list):
        msg = f"Expected list response from Trakt path {path}"
        raise TypeError(msg)
    return [item for item in data if isinstance(item, dict)]


def _request_with_refresh(method: str, path: str) -> requests.Response:
    response = requests.Session().request(
        method,
        f"{BASE_URL}{path}",
        headers=_headers(),
        timeout=30,
    )
    if response.status_code != 401:
        response.raise_for_status()
        return response

    refresh_token()
    response = requests.Session().request(
        method,
        f"{BASE_URL}{path}",
        headers=_headers(),
        timeout=30,
    )
    response.raise_for_status()
    return response


def _headers() -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "trakt-api-version": "2",
        "trakt-api-key": settings.trakt_client_id,
        "Authorization": f"Bearer {settings.trakt_access_token}",
    }


def _normalize_watchlist_item(item: dict[str, Any]) -> dict[str, Any] | None:
    media_type = item.get("type")
    if media_type not in {"movie", "show"}:
        return None

    media = item.get(media_type)
    if not isinstance(media, dict):
        return None

    ids = media.get("ids")
    if not isinstance(ids, dict):
        return None

    trakt_id = ids.get("trakt")
    if not isinstance(trakt_id, int):
        return None

    tmdb_id = ids.get("tmdb")
    return {
        "trakt_id": trakt_id,
        "media_type": media_type,
        "title": str(media.get("title", "")),
        "tmdb_id": tmdb_id if isinstance(tmdb_id, int) else None,
    }


def _item_trakt_id(item: dict[str, Any]) -> int | None:
    for media_type in ("movie", "show"):
        media = item.get(media_type)
        if not isinstance(media, dict):
            continue
        ids = media.get("ids")
        if not isinstance(ids, dict):
            continue

        trakt_id = ids.get("trakt")
        if isinstance(trakt_id, int):
            return trakt_id
    return None
