import pytest

from quetz_client.client import QuetzClient

from .conftest import temporary_package_file


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
    mock_client: QuetzClient,
    role,
    requests_mock,
    mock_server: str,
):
    username = "user"
    url = f"{mock_server}/api/users/{username}/role"
    requests_mock.get(url, json={"role": role})
    actual_role = mock_client.get_role(username)
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
def test_mock_set_channel_member(
    mock_client: QuetzClient,
    role,
    requests_mock,
    mock_server: str,
):
    channel = "a"
    username = "user"

    url = f"{mock_server}/api/channels/{channel}/members"
    requests_mock.post(url, json=None)

    mock_client.set_channel_member(username, role, channel)

    last_request = requests_mock.request_history[0]
    assert last_request.method == "POST"
    assert last_request.json()["username"] == username
    assert last_request.json()["role"] == role


def test_mock_delete_channel_member(
    mock_client: QuetzClient,
    requests_mock,
    mock_server: str,
):
    channel = "a"
    username = "a"

    url = f"{mock_server}/api/channels/{channel}/members"
    requests_mock.delete(url, json=None)

    mock_client.delete_channel_member(username, channel)

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
def test_mock_set_role(
    mock_client: QuetzClient,
    role,
    requests_mock,
    mock_server: str,
):
    username = "user"

    url = f"{mock_server}/api/users/{username}/role"
    requests_mock.put(url, json=None)

    mock_client.set_role(username, role)

    last_request = requests_mock.request_history[0]
    assert last_request.method == "PUT"
    assert last_request.json()["role"] == role
    assert len(last_request.json()) == 1


def test_mock_set_channel(
    mock_client: QuetzClient,
    requests_mock,
    mock_server: str,
):
    channel = "a"

    url = f"{mock_server}/api/channels"
    requests_mock.post(url, json=None)

    mock_client.set_channel(channel)

    last_request = requests_mock.request_history[0]
    assert last_request.method == "POST"
    assert last_request.json()["name"] == channel


def test_mock_delete_channel(
    mock_client: QuetzClient,
    requests_mock,
    mock_server: str,
):
    channel = "a"

    url = f"{mock_server}/api/channels/{channel}"
    requests_mock.delete(url, json=None)

    mock_client.delete_channel(channel)

    last_request = requests_mock.request_history[0]
    assert last_request.method == "DELETE"


def test_mock_yield_packages(mock_client: QuetzClient, expected_packages):
    channel = "channel1"
    package_set = {
        (p.name, p.url, p.current_version) for p in mock_client.yield_packages(channel)
    }
    assert {
        (ep["name"], ep["url"], ep["current_version"])
        for ep in expected_packages["result"]
    } == package_set


def test_mock_post_file_to_channel(
    mock_client: QuetzClient,
    requests_mock,
    mock_server: str,
):
    channel = "a"

    url = f"{mock_server}/api/channels/{channel}/upload/xtensor-0.16.1-0.tar.bz2"
    requests_mock.post(url, json=None)

    requests_mock.register_uri(
        "GET",
        "https://conda.anaconda.org/conda-forge/linux-64/xtensor-0.16.1-0.tar.bz2",
        real_http=True,
    )

    with temporary_package_file() as file:
        mock_client.post_file_to_channel(channel, file)

    # the last request here might be the download of the test package file
    # thus we need to access all the requests
    assert len(requests_mock.request_history) <= 2
    assert any(r.method == "POST" for r in requests_mock.request_history)
