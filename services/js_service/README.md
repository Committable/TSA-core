
# enviroment prerequirement
sudo apt-get install graphviz-dev

docker build -f ./services/js_service/Dockerfile --build-arg "http_proxy=http://192.168.177.1:7890" --build-arg "https_proxy=http://192.168.177.1:7890" --build-arg BUILDKIT_INLINE_CACHE=1 --cache-from=jsbuilder --cache-from=js-analysis-docker -t js-analysis-docker .

docker build -f ./services/js_service/Dockerfile --build-arg "http_proxy=http://192.168.177.1:7890" --build-arg "https_proxy=http://192.168.177.1:7890" --cache-from=jsbuilder --target jsbuilder -t jsbuilder .