
# enviroment prerequirement
sudo apt-get install graphviz-dev

docker build -f ./solidity_service/Dockerfile --build-arg "http_proxy=http://192.168.177.1:7890" --build-arg "https_proxy=http://192.168.177.1:7890" --build-arg BUILDKIT_INLINE_CACHE=1 --cache-from=soliditybuilder --cache-from=solidity-analysis-docker -t solidity-analysis-docker .

docker build -f ./solidity_service/Dockerfile --build-arg "http_proxy=http://192.168.177.1:7890" --build-arg "https_proxy=http://192.168.177.1:7890" --cache-from=soliditybuilder --target soliditybuilder -t soliditybuilder .