import pytest

from quetz_client.client import QuetzClient

from .conftest import temporary_package_file


@pytest.mark.parametrize(
    "role",
    [
        "member",
        "maintainer",
        "owner",
    ],
)
def test_live_set_channel_member(
    live_client: QuetzClient,
    live_post_channel_a,
    role,
):
    live_client.set_channel_member("alice", role, "a")

    members = live_client.yield_channel_members("a")

    assert any(m.user.username == "alice" and m.role == role for m in members)


def test_live_delete_channel_member(
    authed_session,
    live_client: QuetzClient,
    live_post_channel_a_members,
):
    # Check that alice is a member of channel a
    channel = "a"
    username = "alice"

    response = authed_session.get(
        f"{live_client.url}/api/channels/{channel}/members",
    )
    assert {u["user"]["username"] for u in response.json()} == {"alice", "bob"}

    live_client.delete_channel_member(username, channel)

    # Check that alice is no longer a member of channel a
    response = authed_session.get(
        f"{live_client.url}/api/channels/{channel}/members",
    )
    assert {u["user"]["username"] for u in response.json()} == {"bob"}


def test_live_get_role(
    live_client: QuetzClient,
    live_alice_role,
):
    actual_alice_role = live_client.get_role("alice")
    assert next(actual_alice_role).role == live_alice_role


def test_live_post_file_to_channel(
    live_client: QuetzClient,
    live_post_channel_a,
    requests_mock,
):
    # For some reason, we still need to explicitly tell requests_mock to
    # use the real http connection for this url.
    # I thought this would be avoided by using real_http=True in
    # live_client in conftest.py, but it's not.
    requests_mock.register_uri(
        "GET",
        "https://conda.anaconda.org/conda-forge/linux-64/xtensor-0.16.1-0.tar.bz2",
        real_http=True,
    )

    packages = live_client.yield_packages("a")
    assert len(list(packages)) == 0

    with temporary_package_file() as file:
        live_client.post_file_to_channel("a", file)

    packages = live_client.yield_packages("a")

    assert any(p.name == "xtensor" for p in packages)
