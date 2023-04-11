import os
from typing import Optional, cast

import fire
from requests.adapters import HTTPAdapter, Retry

from quetz_client.client import QuetzClient


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
    url = cast(str, url or os.getenv("QUETZ_SERVER_URL", ""))
    token = cast(str, token or os.getenv("QUETZ_API_KEY", ""))
    client = QuetzClient.from_token(url, token)

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
