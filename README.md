# quetz-client

A Python client to interact with a Quetz server.

## Installation

You can install the package in development mode using:

```bash
git clone git@github.com:mamba-org/quetz-client.git
cd quetz-client

# create and activate a fresh environment named quetz-client
# see environment.yml for details
mamba env create
conda activate quetz-client

pre-commit install
pip install --no-build-isolation -e .
```

## Usage

### Python Client

```py
from quetz_client import QuetzClient

url = ""  # URL to your Quetz server
token = ""  # API token for your Quetz server

client = QuetzClient.from_token(url, token)

for channel in client.yield_channels():
    print(channel)
```

### CLI Client

```sh
export QUETZ_SERVER_URL=""  # URL to your Quetz server
export QUETZ_API_KEY=""  # API token for your Quetz server

quetz-client --help
```
