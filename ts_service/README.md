
# enviroment prerequirement
sudo apt-get install graphviz-dev

docker build -f ./ts_service/Dockerfile --build-arg "http_proxy=http://192.168.177.1:7890" --build-arg "https_proxy=http://192.168.177.1:7890" --build-arg BUILDKIT_INLINE_CACHE=1 --cache-from=tsbuilder --cache-from=ts-analysis-docker -t ts-analysis-docker .

docker build -f ./ts_service/Dockerfile --build-arg "http_proxy=http://192.168.177.1:7890" --build-arg "https_proxy=http://192.168.177.1:7890" --cache-from=tsbuilder --target tsbuilder -t tsbuilder .