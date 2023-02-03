import re
import shutil
from contextlib import contextmanager
from pathlib import Path
import socket
from tempfile import NamedTemporaryFile
import time
from typing import Iterator

import pytest
import requests

from quetz_client.client import QuetzClient, User

from quetz.cli import run

from requests_mock import ANY, Mocker

from dacite import from_dict


@contextmanager
def temporary_package_file() -> Iterator[Path]:
    url = "https://conda.anaconda.org/conda-forge/linux-64/xtensor-0.16.1-0.tar.bz2"
    with requests.get(url, stream=True) as response:
        with NamedTemporaryFile() as file:
            with open(file.name, "wb") as fp:
                shutil.copyfileobj(response.raw, fp)
            yield Path(file.name)


@pytest.fixture(scope="module")
def test_url():
    return "https://test.server"


@pytest.fixture(scope="module")
def live_url():
    return "http://localhost:8000"

def wait_for_port(port: int, host: str = 'localhost', timeout: float = 5.0):
    """Wait until a port starts accepting TCP connections.
    Args:
        port: Port number.
        host: Host address on which the port should exist.
        timeout: In seconds. How long to wait before raising errors.
    Raises:
        TimeoutError: The port isn't accepting connection after time specified in `timeout`.
    """
    start_time = time.perf_counter()
    while True:
        try:
            with socket.create_connection((host, port), timeout=timeout):
                break
        except OSError as ex:
            time.sleep(0.01)
            if time.perf_counter() - start_time >= timeout:
                raise TimeoutError('Waited too long for the port {} on host {} to start accepting '
                                   'connections.'.format(port, host)) from ex


@pytest.fixture(scope="module")
def start_server():
    """Start the server in a separate thread"""
    path_to_quetz = "/home/simon/mambaforge/envs/quetz-client/bin/quetz" # "/home/runner/micromamba-root/envs/quetz-client/bin/quetz"
    # breakpoint()
    import subprocess
    server_process = subprocess.Popen([
        path_to_quetz,
        "run",
        "quetz_test",
        "--copy-conf",
        "dev_config.toml",
        "--dev",
        "--delete"
    ])
    if server_process.poll() is not None:
        raise RuntimeError("Server process failed to start")
    wait_for_port(8000)

    yield

    server_process.terminate()
    server_process.wait()


@pytest.fixture
def quetz_client(test_url):
    return QuetzClient(url=test_url, session=requests.Session())

@pytest.fixture(scope="module")
def authed_session(live_url, start_server):
    session = requests.Session()
    response = session.get(f"{live_url}/api/dummylogin/alice")
    assert response.status_code == 200
    return session

@pytest.fixture(scope="module")
def live_quetz_client(live_url, authed_session, start_server):
    # Relay matching requests to the real server
    with Mocker(session=authed_session) as m:
        m.register_uri(ANY, re.compile(re.escape(live_url)), real_http=True)
        yield QuetzClient(url=live_url, session=authed_session)


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


@pytest.fixture(scope="module")
def expected_channel_members(live_alice):
    return [{
        'role': 'owner', 
        'user': {
            'id': live_alice.id, 
            'username': 'alice', 
            'profile': {
                'name': 'Alice',
                'avatar_url': '/avatar.jpg'
            }
        }
    }]

# @pytest.fixture(autouse=True)
# def live_users

@pytest.fixture(autouse=True, scope="module")
def live_post_channel(authed_session, live_url):
    # Add channel a to the live server
    response = authed_session.post(
        f"{live_url}/api/channels",
        json={
            "name": "a",
            "description": "descr a",
            "private": True,
            "size_limit": None,
            "ttl": 36000,
            "mirror_channel_url": None,
            "mirror_mode": None,
        },
    )
    assert response.status_code == 201


@pytest.fixture(autouse=True, scope="module")
def live_users(authed_session, live_url):
    # Get the live users alice, bob, carol, and dave
    response = authed_session.get(f"{live_url}/api/users")
    assert response.status_code == 200
    users = response.json()
    assert len(users) == 4
    assert users[0]["username"] == "alice"
    assert users[1]["username"] == "bob"
    assert users[2]["username"] == "carol"
    assert users[3]["username"] == "dave"

    # Turn json into users
    return [from_dict(User, u) for u in users]

@pytest.fixture(scope="module")
def live_alice(live_users):
    alices = [u for u in live_users if u.username == "alice"]
    assert len(alices) == 1
    return alices[0]

@pytest.fixture(autouse=True, scope="module")
def live_post_channel_members(authed_session, live_url, live_alice):
    # Add alice to channel a
    response = authed_session.post(
        f"{live_url}/api/channels/a/members",
        json={
            "username": live_alice.username,
            "role": "owner",
        },
    )
    assert response.status_code == 201


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
