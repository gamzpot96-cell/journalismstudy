import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient
from app import main, its_api, database

client = TestClient(main.app)
PARAMS = dict(min_x=126.8, max_x=127.0, min_y=37.4, max_y=37.6)
ITEM = dict(roadName="테스트", speed="60", travelTime="12", createdDate="20261013103000", coordX="126.9", coordY="37.5")
DATA = {"header": {"resultCode": "00"}, "body": {"items": [ITEM]}}

@pytest.mark.parametrize("path", ["/", "/map", "/static/index.html"])
def test_static_paths(path):
    assert client.get(path).status_code == 200

@pytest.mark.parametrize("change", [{"min_x": 128}, {"min_y": 40}, {"max_x": 181}, {"min_y": "nan"}, {"max_y": "inf"}])
def test_invalid_bbox(change):
    with patch.object(main, "get_traffic_information", new_callable=AsyncMock) as fetch:
        assert client.get("/traffic", params={**PARAMS, **change}).status_code == 422
        fetch.assert_not_called()

def test_save_failure_preserves_live_data():
    with patch.object(main, "get_traffic_information", AsyncMock(return_value=DATA)), patch.object(main, "save_traffic_information_list", side_effect=RuntimeError):
        response = client.get("/traffic", params=PARAMS)
        assert response.status_code == 200
        assert response.json() == DATA

def test_save_has_coordinates_and_korean_timezone():
    with patch.object(main, "get_traffic_information", AsyncMock(return_value=DATA)), patch.object(main, "save_traffic_information_list", return_value=1) as save:
        assert client.get("/traffic", params=PARAMS).status_code == 200
        row = save.call_args.args[0][0]
        assert row[6:8] == (37.5, 126.9)
        assert row[8].utcoffset().total_seconds() == 32400

def test_fallback_bbox():
    with patch.object(main, "get_traffic_information", AsyncMock(side_effect=httpx.ConnectError("offline"))), patch.object(main, "get_recent_traffic_list", return_value=[ITEM]) as backup:
        response = client.get("/traffic", params=PARAMS)
        assert response.status_code == 200
        assert response.json()["body"]["items"] == [ITEM]
        assert backup.call_args.kwargs == {**PARAMS, "limit": 200}

def test_both_sources_fail():
    with patch.object(main, "get_traffic_information", AsyncMock(side_effect=ValueError)), patch.object(main, "get_recent_traffic_list", side_effect=RuntimeError):
        assert client.get("/traffic", params=PARAMS).status_code == 503

@pytest.mark.parametrize("location", ["", "   ", "a" * 101])
def test_invalid_search(location):
    assert client.get("/traffic/search", params={"location": location}).status_code == 422

@pytest.mark.parametrize("payload", [[], {}, {"header": {"resultCode": "99"}, "body": {"items": []}}, {"body": {"items": [None]}}, {"body": {"items": {}}}])
def test_its_bad_payload(payload):
    response = httpx.Response(200, json=payload, request=httpx.Request("GET", "https://example.com"))
    with patch.object(its_api, "ITS_API_KEY", "secret"), patch.object(httpx.AsyncClient, "get", AsyncMock(return_value=response)):
        with pytest.raises(ValueError):
            asyncio.run(its_api.get_traffic_information(**PARAMS))

def test_its_valid_empty_response():
    response = httpx.Response(200, json={"body": {"items": []}}, request=httpx.Request("GET", "https://example.com"))
    with patch.object(its_api, "ITS_API_KEY", "secret"), patch.object(httpx.AsyncClient, "get", AsyncMock(return_value=response)):
        assert asyncio.run(its_api.get_traffic_information(**PARAMS)) == {"body": {"items": []}}

def test_db_failure_is_not_empty_success():
    with patch.object(database, "get_database_connection", side_effect=RuntimeError):
        with pytest.raises(RuntimeError):
            database.get_recent_traffic_list(**PARAMS)
        with pytest.raises(RuntimeError):
            database.create_traffic_table()

def test_backup_coordinates_timezone_and_query():
    conn = MagicMock()
    cursor = conn.__enter__.return_value.cursor.return_value.__enter__.return_value
    cursor.fetchall.return_value = [("road", "all", "link", 60, 12, "원활", datetime(2026, 10, 13, 1, 30, tzinfo=timezone.utc), 37.5, 126.9)]
    with patch.object(database, "get_database_connection", return_value=conn):
        items = database.get_recent_traffic_list(**PARAMS)
    assert items[0]["createdDate"] == "20261013103000"
    assert items[0]["coordX"] == "126.9"
    assert items[0]["coordY"] == "37.5"
    assert cursor.execute.call_args.args[1] == (126.8, 127.0, 37.4, 37.6, 200)

def test_location_includes_map_center():
    response = httpx.Response(200, json={"documents": [{"x": "126.98", "y": "37.56"}]}, request=httpx.Request("GET", "https://example.com"))
    with patch.object(main, "KAKAO_REST_API_KEY", "secret"), patch.object(httpx.AsyncClient, "get", AsyncMock(return_value=response)), patch.object(main, "traffic", AsyncMock(return_value=DATA)):
        result = client.get("/traffic/search", params={"location": "서울"})
    assert result.json()["location"] == {"name": "서울", "x": 126.98, "y": 37.56}

@pytest.mark.parametrize("payload,status", [({}, 502), ([], 502), ({"documents": []}, 404), ({"documents": [{}]}, 502), ({"documents": [{"x": "nan", "y": "37"}]}, 502)])
def test_search_bad_payload(payload, status):
    response = httpx.Response(200, json=payload, request=httpx.Request("GET", "https://example.com"))
    with patch.object(main, "KAKAO_REST_API_KEY", "secret"), patch.object(httpx.AsyncClient, "get", AsyncMock(return_value=response)):
        assert client.get("/traffic/search", params={"location": "서울"}).status_code == status

def test_missing_kakao_key():
    with patch.object(main, "KAKAO_REST_API_KEY", None):
        assert client.get("/traffic/search", params={"location": "서울"}).status_code == 500

@pytest.mark.parametrize("status", [401, 500])
def test_its_http_error(status):
    response = httpx.Response(status, request=httpx.Request("GET", "https://example.com"))
    with patch.object(its_api, "ITS_API_KEY", "secret"), patch.object(httpx.AsyncClient, "get", AsyncMock(return_value=response)):
        with pytest.raises(httpx.HTTPStatusError):
            asyncio.run(its_api.get_traffic_information(**PARAMS))

def test_missing_its_key():
    with patch.object(its_api, "ITS_API_KEY", None):
        with pytest.raises(ValueError):
            asyncio.run(its_api.get_traffic_information(**PARAMS))
