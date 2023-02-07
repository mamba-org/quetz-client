set -e

git clone https://github.com/mamba-org/quetz.git

pip install -e ./quetz-client
micromamba install quetz
micromamba install sqlalchemy=1.4.46

quetz run test_quetz --copy-conf ./quetz/dev_config.toml --dev --reload > quetz.log &
sleep 5
export QUETZ_API_KEY=(sed -n 's/.*key created for user.*: \(.*\)/\1/p' quetz.log)

bash ./quetz/download-test-package.sh

quetz-client http://localhost:8000/api/channels/channel0 xtensor/linux-64/xtensor-0.16.1-0.tar.bz2 xtensor/osx-64/xtensor-0.16.1-0.tar.bz2

mamba install --override-channels -c http://localhost:8000/get/channel0 -y xtensor
