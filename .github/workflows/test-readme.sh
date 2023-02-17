set -e

# Run the steps described in the quetz README.md for uploading and installing a sample package

pip install -e ./quetz-client

quetz run test_quetz --copy-conf ./quetz/dev_config.toml --dev --reload > quetz.log &
sleep 10
export QUETZ_API_KEY=$(sed -n 's/.*key created for user.*: \(.*\)/\1/p' quetz.log)
export QUETZ_SERVER_URL=http://localhost:8000

mkdir -p xtensor/osx-64
mkdir -p xtensor/linux-64
wget https://conda.anaconda.org/conda-forge/osx-64/xtensor-0.16.1-0.tar.bz2 -P xtensor/osx-64/
wget https://conda.anaconda.org/conda-forge/linux-64/xtensor-0.16.1-0.tar.bz2 -P xtensor/linux-64/

quetz-client post_file_to_channel channel0 xtensor/linux-64/xtensor-0.16.1-0.tar.bz2
quetz-client post_file_to_channel channel0 xtensor/osx-64/xtensor-0.16.1-0.tar.bz2

sleep 2

micromamba install --override-channels --strict-channel-priority -c http://localhost:8000/get/channel0 -c conda-forge xtensor
