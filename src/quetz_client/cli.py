import json
import os
from typing import Optional, Union, cast
from urllib.parse import urlparse

import fire
from requests.adapters import HTTPAdapter, Retry

from quetz_client.client import QuetzClient


class BearerToken:
    def __init__(self, token: str):
        self.token = token

    def __str__(self):
        return self.token


class ApiKey:
    def __init__(self, token: str):
        self.token = token

    def __str__(self):
        return self.token


def get_auth_token_from_file(file: str, url: str):
    """
    Attempt to load the token from the `authentication.json` file that
    is created by `micromamba auth login`.
    """
    with open(file) as f:
        auth = json.load(f)

    # check if the host is present in the authentication file
    host = urlparse(url).netloc

    if host in auth:
        credentials = auth[host]

        if credentials["type"] == "BearerToken":
            return BearerToken(credentials["token"])
        elif credentials["type"] == "ApiKey":
            return ApiKey(credentials["token"])

    return None


def get_auth_token(
    url: str, token: Optional[str], bearer_token: Optional[str]
) -> Union[ApiKey, BearerToken, None]:
    if token:
        return ApiKey(str(token))
    elif bearer_token is not None:
        return BearerToken(str(bearer_token))

    # open the authentication file and read the token
    mamba_auth = os.path.expanduser("~/.mamba/auth/authentication.json")
    return get_auth_token_from_file(mamba_auth, url)


def get_client(
    *,
    url: Optional[str] = None,
    token: Optional[str] = None,
    insecure: bool = False,
    retry: bool = False,
) -> QuetzClient:
    """
    CLI tool to interact with a Quetz server.

    Parameters
    ----------
    url: Optional[str]
        The url of the quetz server.
        Defaults to the `QUETZ_SERVER_URL` environment variable.

    token: Optional[str]
        The API key needed to authenticate with the server.
        Defaults to the `QUETZ_API_KEY` environment variable.

    insecure: bool
        Allow quetz-client to perform "insecure" SSL connections.

    retry: bool
        Allow to retry requests on transient errors and 5xx server
        respones.
    """
    # Initialize the client (do not force the env variables to be set of help on the
    # subcommands does not work without setting them)
    url = url or os.getenv("QUETZ_SERVER_URL")

    if not url:
        raise ValueError("Please specify a server url with --url or QUETZ_SERVER_URL")

    token = token or os.getenv("QUETZ_API_KEY")
    bearer_token = os.getenv("QUETZ_BEARER_TOKEN")

    parsed_token = get_auth_token(url, token, bearer_token)

    if isinstance(parsed_token, BearerToken):
        client = QuetzClient.from_bearer_token(url, str(parsed_token))
    elif isinstance(parsed_token, ApiKey):
        client = QuetzClient.from_token(url, str(parsed_token))
    else:
        raise ValueError(
            "Please specify a token with --token or QUETZ_API_KEY or "
            "QUETZ_BEARER_TOKEN or login with `micromamba auth login`"
        )

    # Configure the client with additional flags passed to the CLI
    client.session.verify = not insecure
    if retry:
        # Retry a total of 10 times, starting with an initial backoff of one second.
        retry_config = Retry(
            total=10,
            status_forcelist=range(500, 600),
            backoff_factor=1,
            allowed_methods=["GET", "POST", "PUT", "DELETE"],
        )
        adapter = HTTPAdapter(max_retries=retry_config)
        client.session.mount(url, adapter)

    return client


def main() -> None:
    fire.Fire(get_client)
