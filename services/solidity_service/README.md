
# enviroment prerequirement

docker build -f ./services/solidity_service/Dockerfile --build-arg "http_proxy=http://192.168.177.1:7890" --build-arg "https_proxy=http://192.168.177.1:7890" --cache-from=soliditybuilder --target soliditybuilder -t soliditybuilder .

docker build -f ./services/solidity_service/Dockerfile --build-arg "http_proxy=http://192.168.177.1:7890" --build-arg "https_proxy=http://192.168.177.1:7890" --build-arg BUIL
DKIT_INLINE_CACHE=1 --cache-from=soliditybuilder --cache-from=solidity-analysis-docker -t solidity-analysis-docker .

