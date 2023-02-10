set -e

# Run the steps described in the quetz README.md for uploading and installing a sample package

git clone -b fix-upload-again https://github.com/simonbohnen/quetz.git

pip install -e ./quetz-client
# micromamba uninstall -y quetz
micromamba install -y sqlalchemy=1.4.46
pip install -e ./quetz

quetz run test_quetz --copy-conf ./quetz/dev_config.toml --dev --reload > quetz.log &
sleep 10
export QUETZ_API_KEY=$(sed -n 's/.*key created for user.*: \(.*\)/\1/p' quetz.log)
# echo "PRINTING API KEY"
# echo $QUETZ_API_KEY
export QUETZ_SERVER_URL=http://localhost:8000

bash ./quetz/download-test-package.sh

quetz-client post_files_to_channel channel0 xtensor/linux-64/xtensor-0.16.1-0.tar.bz2 xtensor/osx-64/xtensor-0.16.1-0.tar.bz2

sleep 2

micromamba install --override-channels --strict-channel-priority -c http://localhost:8000/get/channel0 -c conda-forge xtensor
