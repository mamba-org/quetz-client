from dacite import from_dict

from quetz_client.client import Channel, ChannelMember, QuetzClient


def test_from_token():
    token = "abc"
    quetz_client = QuetzClient.from_token("", token)
    assert quetz_client.session.headers.get("X-API-Key") == token


def test_yield_channels(client: QuetzClient, three_channels):
    channels = list(client.yield_channels(limit=2, query="c-"))
    assert len(channels) == 3
    assert isinstance(channels[0], Channel)
    assert {from_dict(Channel, c) for c in three_channels} == set(channels)


def test_yield_channel_members(
    client: QuetzClient, expected_channel_a_members, live_post_channel_a_members
):
    channel = "a"
    channel_members = set(client.yield_channel_members(channel=channel))
    assert {
        from_dict(ChannelMember, ecm) for ecm in expected_channel_a_members
    } == channel_members


def test_yield_users(client: QuetzClient, expected_users):
    users = list(client.yield_users())
    user_set = {(user.id, user.username) for user in users}
    expected_set = {(user["id"], user["username"]) for user in expected_users["result"]}
    assert user_set == expected_set
