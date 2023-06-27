
# enviroment prerequirement

docker build -f ./services/solidity_service/Dockerfile --cache-from=soliditybuilder --target soliditybuilder -t soliditybuilder .

docker build -f ./services/solidity_service/Dockerfile --build-arg BUILDKIT_INLINE_CACHE=1 --cache-from=soliditybuilder --cache-from=solidity-analysis-docker -t solidity-analysis-docker .

