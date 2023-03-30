
# enviroment prerequirement
sudo apt-get install graphviz-dev

docker build -f ./evm_service/Dockerfile --build-arg "http_proxy=http://192.168.177.1:7890" --build-arg "https_proxy=http://192.168.177.1:7890" --build-arg BUILDKIT_INLINE_CACHE=1 --cache-from=evmbuilder --cache-from=evm-analysis-docker -t evm-analysis-docker .

docker build -f ./evm_service/Dockerfile --build-arg "http_proxy=http://192.168.177.1:7890" --build-arg "https_proxy=http://192.168.177.1:7890" --cache-from=evmbuilder --target evmbuilder -t evmbuilder .