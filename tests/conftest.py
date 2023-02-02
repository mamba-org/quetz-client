import re
import shutil
from contextlib import contextmanager
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Iterator

import pytest
import requests

from quetz_client.client import QuetzClient


@contextmanager
def temporary_package_file() -> Iterator[Path]:
    url = "https://conda.anaconda.org/conda-forge/linux-64/xtensor-0.16.1-0.tar.bz2"
    with requests.get(url, stream=True) as response:
        with NamedTemporaryFile() as file:
            with open(file.name, "wb") as fp:
                shutil.copyfileobj(response.raw, fp)
            yield Path(file.name)


@pytest.fixture
def test_url():
    return "https://test.server"


@pytest.fixture
def quetz_client(test_url):
    return QuetzClient(url=test_url, session=requests.Session())


@pytest.fixture(autouse=True)
def mock_default_paginated_empty(requests_mock, test_url):
    url = re.escape(f"{test_url}/api/paginated/") + r".*\?.*skip=20.*"
    requests_mock.get(
        re.compile(url),
        json={
            "pagination": {"skip": 20, "limit": 20, "all_records_count": 19},
            "result": [],
        },
    )


@pytest.fixture(autouse=True)
def mock_yield_channels_0(requests_mock, test_url):
    url = f"{test_url}/api/paginated/channels?skip=0"
    mock_resp = {
        "pagination": {"skip": 0, "limit": 2, "all_records_count": 3},
        "result": [
            {
                "name": "a",
                "description": "descr a",
                "private": True,
                "size_limit": None,
                "ttl": 36000,
                "mirror_channel_url": None,
                "mirror_mode": None,
                "members_count": 42,
                "packages_count": 11,
            },
            {
                "name": "b",
                "description": "descr b",
                "private": True,
                "size_limit": None,
                "ttl": 36000,
                "mirror_channel_url": None,
                "mirror_mode": None,
                "members_count": 42,
                "packages_count": 11,
            },
        ],
    }
    requests_mock.get(url, json=mock_resp)


@pytest.fixture(autouse=True)
def mock_yield_channels_2(requests_mock, test_url):
    url = f"{test_url}/api/paginated/channels?skip=2"
    mock_resp = {
        "pagination": {"skip": 2, "limit": 2, "all_records_count": 3},
        "result": [
            {
                "name": "c",
                "description": "descr c",
                "private": False,
                "size_limit": None,
                "ttl": 36000,
                "mirror_channel_url": None,
                "mirror_mode": None,
                "members_count": 42,
                "packages_count": 11,
            }
        ],
    }
    requests_mock.get(url, json=mock_resp)


@pytest.fixture(autouse=True)
def mock_yield_channels_4(requests_mock, test_url):
    url = f"{test_url}/api/paginated/channels?skip=4"
    requests_mock.get(
        url,
        json={
            "pagination": {"skip": 4, "limit": 2, "all_records_count": 3},
            "result": [],
        },
    )


@pytest.fixture
def expected_channel_members():
    return [{"username": "u1", "role": "owner"}, {"username": "u2", "role": "member"}]


@pytest.fixture(autouse=True)
def mock_yield_channel_members(requests_mock, test_url, expected_channel_members):
    url = f"{test_url}/api/channels/a/members"
    requests_mock.get(url, json=expected_channel_members)


@pytest.fixture
def expected_users():
    return {
        "pagination": {"skip": 0, "limit": 20, "all_records_count": 2},
        "result": [
            {
                "id": "015744e4-af4f-4bc4-a1a6-0c8ae8d14ddc",
                "username": "alice",
                "profile": {"name": "Alice", "avatar_url": "/avatar.jpg"},
            },
            {
                "id": "0a518bff-2e77-4ce9-b36e-ace9d50b1496",
                "username": "bob",
                "profile": {"name": "Bob", "avatar_url": "/avatar.jpg"},
            },
        ],
    }


@pytest.fixture(autouse=True)
def mock_yield_users(requests_mock, test_url, expected_users):
    url = f"{test_url}/api/paginated/users?skip=0"
    requests_mock.get(url, json=expected_users)


@pytest.fixture
def expected_packages():
    return {
        "pagination": {"skip": 0, "limit": 20, "all_records_count": 2},
        "result": [
            {
                "name": "testpackage1",
                "summary": "Summary 1",
                "description": "Description 1",
                "url": "https://github.com/pkg1",
                "platforms": ["linux-64"],
                "current_version": "3.2.0",
                "latest_change": "2022-06-14T17:54:11.430921+00:00",
            },
            {
                "name": "testpackage2",
                "summary": "Summary 2",
                "description": "Description 2",
                "url": "https://github.com/pkg2",
                "platforms": ["noarch"],
                "current_version": "0.0.2",
                "latest_change": "2022-06-14T17:54:11.430921+00:00",
            },
        ],
    }


@pytest.fixture(autouse=True)
def mock_yield_packages(requests_mock, test_url, expected_packages):
    url = f"{test_url}/api/paginated/channels/channel1/packages?skip=0"
    requests_mock.get(url, json=expected_packages)
