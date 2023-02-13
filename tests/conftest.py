import re
import shutil
import socket
import time
from contextlib import contextmanager
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Iterator

import pytest
import requests
from dacite import from_dict
from requests_mock import ANY, Mocker

from quetz_client.client import Channel, QuetzClient, User


@contextmanager
def temporary_package_file() -> Iterator[Path]:
    url = "https://conda.anaconda.org/conda-forge/linux-64/xtensor-0.16.1-0.tar.bz2"
    with requests.get(url, stream=True) as response:
        with NamedTemporaryFile() as file:
            with open(file.name, "wb") as fp:
                shutil.copyfileobj(response.raw, fp)
            yield Path(file.name)


@pytest.fixture(scope="module")
def mock_server():
    return "https://test.server"


@pytest.fixture(scope="module")
def live_server():
    return "http://localhost:8000"


def wait_for_port(port: int, host: str = "localhost", timeout: float = 5.0):
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
                raise TimeoutError(
                    "Waited too long for the port {} on host {} to start accepting "
                    "connections.".format(port, host)
                ) from ex


@pytest.fixture(scope="module")
def start_server():
    """Start the server in a separate thread"""
    # "/home/simon/mambaforge/envs/quetz-client/bin/quetz"
    # "/home/runner/micromamba-root/envs/quetz-client/bin/quetz"
    path_to_quetz = "/home/simon/mambaforge/envs/quetz-client/bin/quetz"
    # breakpoint()
    import subprocess

    server_process = subprocess.Popen(
        [
            path_to_quetz,
            "run",
            "quetz_test",
            "--copy-conf",
            "tests/dev_config.toml",
            "--dev",
            "--delete",
        ]
    )
    if server_process.poll() is not None:
        raise RuntimeError("Server process failed to start")
    wait_for_port(8000)

    yield

    server_process.terminate()
    server_process.wait()


@pytest.fixture
def mock_client(mock_server):
    return QuetzClient(url=mock_server, session=requests.Session())


@pytest.fixture(scope="module")
def authed_session(live_server, start_server):
    session = requests.Session()
    response = session.get(f"{live_server}/api/dummylogin/alice")
    assert response.status_code == 200
    return session


@pytest.fixture(scope="module")
def live_client(live_server, authed_session):
    # Relay matching requests to the real server
    with Mocker(session=authed_session) as m:
        m.register_uri(ANY, re.compile(re.escape(live_server)), real_http=True)
        yield QuetzClient(url=live_server, session=authed_session)


@pytest.fixture(params=[True, False])
def client(request, live_client, mock_client):
    return live_client if request.param else mock_client


@pytest.fixture(autouse=True)
def mock_default_paginated_empty(requests_mock, mock_server):
    url = re.escape(f"{mock_server}/api/paginated/") + r".*\?.*skip=20.*"
    requests_mock.get(
        re.compile(url),
        json={
            "pagination": {"skip": 20, "limit": 20, "all_records_count": 19},
            "result": [],
        },
    )


LIVE_CHANNELS_COUNT = 4


@pytest.fixture
def live_channels(authed_session, live_server, live_post_channel):
    response = authed_session.get(f"{live_server}/api/channels")
    assert response.status_code == 200

    channels = [from_dict(Channel, c) for c in response.json()]
    assert len(channels) == LIVE_CHANNELS_COUNT
    return channels


def get_channel_json(channels, skip, limit):
    return {
        "pagination": {
            "skip": skip,
            "limit": limit,
            "all_records_count": LIVE_CHANNELS_COUNT,
        },
        "result": [
            {
                "name": channels[i].name,
                "description": channels[i].description,
                "private": channels[i].private,
                "size_limit": channels[i].size_limit,
                "ttl": channels[i].ttl,
                "mirror_channel_url": channels[i].mirror_channel_url,
                "mirror_mode": channels[i].mirror_mode,
                "members_count": channels[i].members_count,
                "packages_count": channels[i].packages_count,
            }
            for i in range(skip, skip + limit)
        ],
    }


@pytest.fixture
def expected_channels(live_channels):
    return get_channel_json(live_channels, 0, LIVE_CHANNELS_COUNT)["result"]


@pytest.fixture
def expected_channels_0(live_channels):
    return get_channel_json(live_channels, 0, 2)


@pytest.fixture(autouse=True)
def mock_yield_channels_0(requests_mock, mock_server, expected_channels_0):
    url = f"{mock_server}/api/paginated/channels?skip=0"
    requests_mock.get(url, json=expected_channels_0)


@pytest.fixture
def expected_channels_2(live_channels):
    return get_channel_json(live_channels, 2, 2)


@pytest.fixture(autouse=True)
def mock_yield_channels_2(requests_mock, mock_server, expected_channels_2):
    url = f"{mock_server}/api/paginated/channels?skip=2"
    requests_mock.get(url, json=expected_channels_2)


@pytest.fixture(autouse=True, scope="module")
def live_post_channel(authed_session, live_server):
    # Add channel a to the live server
    response = authed_session.post(
        f"{live_server}/api/channels",
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
def live_users(authed_session, live_server):
    # Get the live users alice, bob, carol, and dave
    response = authed_session.get(f"{live_server}/api/users")
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
    return get_user_with_username(live_users, "alice")


@pytest.fixture(scope="module")
def live_bob(live_users):
    return get_user_with_username(live_users, "bob")


@pytest.fixture(scope="module")
def live_carol(live_users):
    return get_user_with_username(live_users, "carol")


@pytest.fixture(scope="module")
def live_dave(live_users):
    return get_user_with_username(live_users, "dave")


def get_user_with_username(users, username):
    users = [u for u in users if u.username == username]
    assert len(users) == 1
    return users[0]


@pytest.fixture(autouse=True, scope="module")
def live_post_channel_members(authed_session, live_server):
    # Add alice & bob to channel a
    response = authed_session.post(
        f"{live_server}/api/channels/a/members",
        json={
            "username": "alice",
            "role": "owner",
        },
    )
    assert response.status_code == 201
    response = authed_session.post(
        f"{live_server}/api/channels/a/members",
        json={
            "username": "bob",
            "role": "owner",
        },
    )
    assert response.status_code == 201


@pytest.fixture(scope="module")
def expected_channel_members(live_alice, live_bob):
    return [
        {
            "role": "owner",
            "user": {
                "id": live_alice.id,
                "username": "alice",
                "profile": {"name": "Alice", "avatar_url": "/avatar.jpg"},
            },
        },
        {
            "role": "owner",
            "user": {
                "id": live_bob.id,
                "username": "bob",
                "profile": {"name": "Bob", "avatar_url": "/avatar.jpg"},
            },
        },
    ]


@pytest.fixture(autouse=True)
def mock_yield_channel_members(requests_mock, mock_server, expected_channel_members):
    url = f"{mock_server}/api/channels/a/members"
    requests_mock.get(url, json=expected_channel_members)


@pytest.fixture
def expected_users(live_alice, live_bob, live_carol, live_dave):
    return {
        "pagination": {"skip": 0, "limit": 20, "all_records_count": 2},
        "result": [
            {
                "id": live_alice.id,
                "username": "alice",
                "profile": {"name": "Alice", "avatar_url": "/avatar.jpg"},
            },
            {
                "id": live_bob.id,
                "username": "bob",
                "profile": {"name": "Bob", "avatar_url": "/avatar.jpg"},
            },
            {
                "id": live_carol.id,
                "username": "carol",
                "profile": {"name": "Carol", "avatar_url": "/avatar.jpg"},
            },
            {
                "id": live_dave.id,
                "username": "dave",
                "profile": {"name": "Dave", "avatar_url": "/avatar.jpg"},
            },
        ],
    }


@pytest.fixture(autouse=True)
def mock_yield_users(requests_mock, mock_server, expected_users):
    url = f"{mock_server}/api/paginated/users?skip=0"
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
def mock_yield_packages(requests_mock, mock_server, expected_packages):
    url = f"{mock_server}/api/paginated/channels/channel1/packages?skip=0"
    requests_mock.get(url, json=expected_packages)
