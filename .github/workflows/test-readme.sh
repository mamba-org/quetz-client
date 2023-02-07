set -e

git clone https://github.com/mamba-org/quetz.git

pip install -e ./quetz-client
micromamba install quetz
micromamba install -y sqlalchemy=1.4.46

quetz run test_quetz --copy-conf ./quetz/dev_config.toml --dev --reload > quetz.log &
sleep 5
export QUETZ_API_KEY=(sed -n 's/.*key created for user.*: \(.*\)/\1/p' quetz.log)
export QUETZ_SERVER_URL=http://localhost:8000

bash ./quetz/download-test-package.sh

quetz-client post_file_to_channel channel0 xtensor/linux-64/xtensor-0.16.1-0.tar.bz2 # xtensor/osx-64/xtensor-0.16.1-0.tar.bz2

mamba install --override-channels -c http://localhost:8000/get/channel0 -y xtensor
