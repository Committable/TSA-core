
# enviroment prerequirement
sudo apt-get install graphviz-dev

docker build -f ./services/rust_service/Dockerfile --build-arg "http_proxy=http://192.168.177.1:7890" --build-arg "https_proxy=http://192.168.177.1:7890" --build-arg BUILDKIT_INLINE_CACHE=1 --cache-from=rustbuilder --cache-from=rust-analysis-docker -t rust-analysis-docker .

docker build -f ./services/rust_service/Dockerfile --build-arg "http_proxy=http://192.168.177.1:7890" --build-arg "https_proxy=http://192.168.177.1:7890" --cache-from=rustbuilder --target rustbuilder -t rustbuilder .