import hashlib
from dataclasses import dataclass
from itertools import count
from pathlib import Path
from typing import Dict, Iterator, List, Mapping, Optional, Union

import requests


@dataclass(frozen=True)
class Channel:
    name: str
    description: str
    private: bool
    size_limit: Optional[int]
    ttl: int
    mirror_channel_url: Optional[str]
    mirror_mode: Optional[str]
    members_count: int
    packages_count: int


@dataclass(frozen=True)
class ChannelMember:
    username: str
    role: str


@dataclass(frozen=True)
class User:
    id: str
    username: str
    profile: Mapping


@dataclass(frozen=True)
class Role:
    role: str


@dataclass(frozen=True)
class Package:
    name: str
    summary: str
    description: str
    url: str
    platforms: List[str]
    current_version: str
    latest_change: str


@dataclass
class QuetzClient:
    session: requests.Session
    url: str

    @classmethod
    def from_token(cls, url: str, token: str) -> "QuetzClient":
        session = requests.Session()
        session.headers.update({"X-API-Key": token})
        return cls(session, url=url)

    def _yield_paginated(
        self, url: str, params: Dict[str, Union[str, int]], limit: int = 20
    ) -> Iterator[Dict]:
        params = {**params, "limit": limit}
        for skip in count(step=limit):
            params["skip"] = skip
            response = self.session.get(url=url, params=params)
            response.raise_for_status()
            result = response.json()["result"]
            if not result:
                break
            yield from result

    def yield_channels(self, query: str = "", limit: int = 20) -> Iterator[Channel]:
        url = f"{self.url}/api/paginated/channels"
        params: Dict[str, Union[str, int]] = {
            "q": query,
            "public": True,  # include public channels
        }
        for channel_json in self._yield_paginated(
            url=url,
            params=params,
            limit=limit,
        ):
            yield Channel(**channel_json)

    def yield_channel_members(self, channel: str) -> Iterator[ChannelMember]:
        url = f"{self.url}/api/channels/{channel}/members"
        response = self.session.get(url=url)
        response.raise_for_status()
        for member_json in response.json():
            yield ChannelMember(**member_json)

    def yield_users(self, query: str = "", limit: int = 20) -> Iterator[User]:
        url = f"{self.url}/api/paginated/users"
        params: Dict[str, Union[str, int]] = {
            "q": query,
        }
        for user_json in self._yield_paginated(url=url, params=params, limit=limit):
            yield User(**user_json)

    def get_role(self, user: str) -> Iterator[Role]:
        url = f"{self.url}/api/users/{user}/role"
        response = self.session.get(
            url=url,
        )
        response.raise_for_status()
        yield Role(response.json()["role"])

    def set_channel_member(self, user: str, role: Optional[str], channel: str) -> None:
        url = f"{self.url}/api/channels/{channel}/members"
        response = self.session.post(url=url, json={"username": user, "role": role})
        response.raise_for_status()

    def delete_channel_member(self, user: str, channel: str) -> None:
        url = f"{self.url}/api/channels/{channel}/members"
        response = self.session.delete(url=url, params={"username": user})
        response.raise_for_status()

    def set_role(self, user: str, role: Optional[str]) -> None:
        url = f"{self.url}/api/users/{user}/role"
        data = {"role": role}
        response = self.session.put(
            url=url,
            json=data,
        )
        response.raise_for_status()

    def set_channel(
        self,
        channel: str,
        mirror_api_key: str = "",
        register_mirror: bool = False,
        **kwargs,
    ):
        url = f"{self.url}/api/channels"
        params: Dict[str, Union[str, bool]] = {
            "mirror_api_key": mirror_api_key,
            "register_mirror": register_mirror,
        }
        response = self.session.post(
            url=url, json={"name": channel, **kwargs}, params=params
        )
        response.raise_for_status()

    def delete_channel(self, channel: str):
        url = f"{self.url}/api/channels/{channel}"
        response = self.session.delete(
            url=url,
        )
        response.raise_for_status()

    def yield_packages(
        self, channel: str, query: str = "", limit: int = 20, order_by: str = ""
    ) -> Iterator[Package]:
        url = f"{self.url}/api/paginated/channels/{channel}/packages"
        params: Dict[str, Union[str, int]] = {
            "q": query,
            "order_by": order_by,
        }
        for user_json in self._yield_paginated(url=url, params=params, limit=limit):
            yield Package(**user_json)

    def post_file_to_channel(self, channel: str, file: Path, force: bool = False):
        url = f"{self.url}/api/channels/{channel}/upload/{file.name}"
        body = open(file, "rb")

        upload_hash = hashlib.sha256(body.read()).hexdigest()

        params: Dict[str, Union[str, int]] = {
            "force": force,
            "sha256": upload_hash,
        }
        response = self.session.post(
            url=url,
            data=body,
            params=params,
        )
        response.raise_for_status()
