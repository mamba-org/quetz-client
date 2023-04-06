import os
from typing import Optional

import fire

from quetz_client.client import QuetzClient


def get_client(
    *, url: Optional[str] = None, token: Optional[str] = None, insecure: bool = False
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
        Allow quetz-client to perform "insecure" SSL connections
        and transfers.
    """
    url = url or os.environ.get("QUETZ_SERVER_URL")
    token = token or os.environ.get("QUETZ_API_KEY")
    client = QuetzClient.from_token(url, token, insecure=insecure)
    return client


def main() -> None:
    fire.Fire(get_client)
