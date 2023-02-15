import os
import re
import shutil
import socket
import time
from contextlib import contextmanager
from dataclasses import asdict
from pathlib import Path
from typing import Iterator

import pytest
import requests
from dacite import from_dict
from requests_mock import Mocker

from quetz_client.client import Channel, QuetzClient, User

# Resources created here:
# Channels, channel memberships, packages
#
# Resources created by quetz on start:
# Users: alice, bob, carol, dave
# API key for one of the users
# See _fill_test_database in cli.py in quetz


@contextmanager
def temporary_package_file() -> Iterator[Path]:
    path = Path.home() / "xtensor-0.16.1-0.tar.bz2"

    if path.exists():
        yield path
        return

    url = "https://conda.anaconda.org/conda-forge/linux-64/xtensor-0.16.1-0.tar.bz2"
    with requests.get(url, stream=True) as response:
        with open(path, "wb") as file:
            shutil.copyfileobj(response.raw, file)
        yield path


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
    path_to_quetz = "/home/runner/micromamba-root/envs/quetz-client/bin/quetz"
    if not os.path.exists(path_to_quetz):
        path_to_quetz = str(Path.home() / "mambaforge/envs/quetz-client/bin/quetz")

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


@pytest.fixture(scope="module")
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
    with Mocker(session=authed_session, real_http=True):
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


def live_channels(authed_session, live_server):
    response = authed_session.get(f"{live_server}/api/channels")
    assert response.status_code == 200

    channels = [from_dict(Channel, c) for c in response.json()]
    return channels


def get_channel_json(channels, skip, limit):
    return {
        "pagination": {
            "skip": skip,
            "limit": limit,
            "all_records_count": len(channels),
        },
        "result": [
            asdict(c) for c in channels[skip : min(skip + limit, len(channels))]
        ],
    }


@pytest.fixture
def three_channels(
    requests_mock, mock_server, live_post_3_channels, authed_session, live_server
):
    # We don't use live_channels as a fixture here because
    # we want to make sure that the channels are created first
    channels = live_channels(authed_session, live_server)
    # We only want the channels starting with c-
    prefixed_channels = [c for c in channels if c.name.startswith("c-")]

    url = f"{mock_server}/api/paginated/channels?skip=0&q=c-"
    requests_mock.get(url, json=get_channel_json(prefixed_channels, 0, 2))

    url = f"{mock_server}/api/paginated/channels?skip=2&q=c-"
    requests_mock.get(url, json=get_channel_json(prefixed_channels, 2, 2))

    url = f"{mock_server}/api/paginated/channels?skip=4&q=c-"
    requests_mock.get(url, json=get_channel_json([], 4, 2))

    return get_channel_json(prefixed_channels, 0, len(prefixed_channels))["result"]


@pytest.fixture
def live_post_channel_a(authed_session, live_server):
    post_channel(authed_session, live_server, "a", "descr a")
    yield
    delete_channel(authed_session, live_server, "a")


@pytest.fixture
def live_post_3_channels(authed_session, live_server):
    post_channel(authed_session, live_server, "c-1", "descr c1")
    post_channel(authed_session, live_server, "c-2", "descr c2")
    post_channel(authed_session, live_server, "c-3", "descr c3")
    yield
    delete_channel(authed_session, live_server, "c-1")
    delete_channel(authed_session, live_server, "c-2")
    delete_channel(authed_session, live_server, "c-3")


def post_channel(authed_session, live_server, name, description):
    response = authed_session.post(
        f"{live_server}/api/channels",
        json={
            "name": name,
            "description": description,
            "private": True,
            "size_limit": None,
            "ttl": 36000,
            "mirror_channel_url": None,
            "mirror_mode": None,
        },
    )
    assert response.status_code == 201
    return response


def delete_channel(authed_session, live_server, name):
    response = authed_session.delete(f"{live_server}/api/channels/{name}")
    assert response.status_code == 200


@pytest.fixture(autouse=True, scope="module")
def live_users(authed_session, live_server):
    # Get the live users alice, bob, carol, and dave
    # These are created by passing the --dev flag to the live quetz
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


@pytest.fixture
def live_alice_role(authed_session, live_server):
    response = authed_session.get(f"{live_server}/api/users/alice/role")
    assert response.status_code == 200
    return response.json()["role"]


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
    return {u.username: u for u in users}[username]


@pytest.fixture()
def live_post_channel_a_members(authed_session, live_server, live_post_channel_a):
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

    # Channel will be deleted afterwards, so we don't need to remove the members


@pytest.fixture(scope="module")
def expected_channel_a_members(live_alice, live_bob):
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
def mock_yield_channel_a_members(
    requests_mock, mock_server, expected_channel_a_members
):
    url = f"{mock_server}/api/channels/a/members"
    requests_mock.get(url, json=expected_channel_a_members)


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
