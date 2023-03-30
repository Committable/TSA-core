
# enviroment prerequirement
sudo apt-get install graphviz-dev

docker build -f ./move_service/Dockerfile --build-arg "http_proxy=http://192.168.177.1:7890" --build-arg "https_proxy=http://192.168.177.1:7890" --build-arg BUILDKIT_INLINE_CACHE=1 --cache-from=movebuilder --cache-from=move-analysis-docker -t move-analysis-docker .

docker build -f ./move_service/Dockerfile --build-arg "http_proxy=http://192.168.177.1:7890" --build-arg "https_proxy=http://192.168.177.1:7890" --cache-from=movebuilder --target movebuilder -t movebuilder .