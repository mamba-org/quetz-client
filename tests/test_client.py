import re

import pytest

from quetz_client.client import Channel, ChannelMember, QuetzClient

from .conftest import temporary_package_file


def test_yield_channels(quetz_client):
    expected_channel_names = ("a", "b", "c")
    channels = list(quetz_client.yield_channels(limit=2))
    assert len(channels) == 3
    assert isinstance(channels[0], Channel)
    assert {channel.name for channel in channels} == set(expected_channel_names)


def test_yield_channel_members(quetz_client: QuetzClient, expected_channel_members):
    channel = "a"
    channel_members = set(quetz_client.yield_channel_members(channel=channel))
    assert {ChannelMember(**ecm) for ecm in expected_channel_members} == channel_members


def test_yield_users(quetz_client: QuetzClient, expected_users):
    users = list(quetz_client.yield_users())
    user_set = {(user.id, user.username) for user in users}
    expected_set = {(user["id"], user["username"]) for user in expected_users["result"]}
    assert user_set == expected_set


@pytest.mark.parametrize(
    "role",
    [
        None,
        "member",
        "maintainer",
        "owner",
    ],
)
def test_get_role(
    quetz_client: QuetzClient,
    role,
    requests_mock,
    test_url: str,
):
    username = "user"
    url = f"{test_url}/api/users/{username}/role"
    requests_mock.get(url, json={"role": role})
    actual_role = quetz_client.get_role(username)
    assert next(actual_role).role == role


@pytest.mark.parametrize(
    "role",
    [
        None,
        "member",
        "maintainer",
        "owner",
    ],
)
def test_set_channel_member(
    quetz_client: QuetzClient,
    role,
    requests_mock,
    test_url: str,
):
    channel = "a"
    username = "user"

    url = f"{test_url}/api/channels/{channel}/members"
    requests_mock.post(url, json=None)

    quetz_client.set_channel_member(username, role, channel)

    last_request = requests_mock.request_history[0]
    assert last_request.method == "POST"
    assert last_request.json()["username"] == username
    assert last_request.json()["role"] == role


def test_delete_channel_member(
    quetz_client: QuetzClient,
    requests_mock,
    test_url: str,
):
    channel = "a"
    username = "a"

    url = f"{test_url}/api/channels/{channel}/members"
    requests_mock.delete(url, json=None)

    quetz_client.delete_channel_member(username, channel)

    last_request = requests_mock.request_history[0]
    assert last_request.method == "DELETE"
    assert last_request.qs["username"] == [username]
    assert len(last_request.qs) == 1


@pytest.mark.parametrize(
    "role",
    [
        None,
        "member",
        "maintainer",
        "owner",
    ],
)
def test_set_role(
    quetz_client: QuetzClient,
    role,
    requests_mock,
    test_url: str,
):
    username = "user"

    url = f"{test_url}/api/users/{username}/role"
    requests_mock.put(url, json=None)

    quetz_client.set_role(username, role)

    last_request = requests_mock.request_history[0]
    assert last_request.method == "PUT"
    assert last_request.json()["role"] == role
    assert len(last_request.json()) == 1


def test_from_token():
    token = "abc"
    quetz_client = QuetzClient.from_token("", token)
    assert quetz_client.session.headers.get("X-API-Key") == token


def test_set_channel(
    quetz_client: QuetzClient,
    requests_mock,
    test_url: str,
):
    channel = "a"

    url = f"{test_url}/api/channels"
    requests_mock.post(url, json=None)

    quetz_client.set_channel(channel)

    last_request = requests_mock.request_history[0]
    assert last_request.method == "POST"
    assert last_request.json()["name"] == channel


def test_delete_channel(
    quetz_client: QuetzClient,
    requests_mock,
    test_url: str,
):
    channel = "a"

    url = f"{test_url}/api/channels/{channel}"
    requests_mock.delete(url, json=None)

    quetz_client.delete_channel(channel)

    last_request = requests_mock.request_history[0]
    assert last_request.method == "DELETE"


def test_yield_packages(quetz_client: QuetzClient, expected_packages):
    channel = "channel1"
    package_set = {
        (p.name, p.url, p.current_version) for p in quetz_client.yield_packages(channel)
    }
    assert {
        (ep["name"], ep["url"], ep["current_version"])
        for ep in expected_packages["result"]
    } == package_set


def test_post_file_to_channel(
    quetz_client: QuetzClient,
    requests_mock,
    test_url: str,
):
    channel = "a"

    url_matcher = re.compile(
        f"{test_url}/api/channels/{channel}/upload/\\w*\\?force=False&sha256=\\w*"
    )
    requests_mock.register_uri("POST", url_matcher, json=None)

    requests_mock.register_uri(
        "GET",
        "https://conda.anaconda.org/conda-forge/linux-64/xtensor-0.16.1-0.tar.bz2",
        real_http=True,
    )

    with temporary_package_file() as file:
        quetz_client.post_file_to_channel(channel, file)

    # the last request here is the download of the test package file, thus we need to access the second-to-last request
    last_request = requests_mock.request_history[1]
    assert last_request.method == "POST"
