Seraph
======

A Modeling Tool for solidity source files in a git repository, producing graphs and abstraction of ast/cfg/ssg  

[![Gitter][gitter-badge]][gitter-url]
[![License: GPL v3][license-badge]][license-badge-url]
[![Build Status](https://travis-ci.org/melonproject/oyente.svg?branch=master)](https://travis-ci.org/melonproject/oyente)

*This repository is currently maintained by yangzq12 ([@yangzq12](https://github.com/yangzq12)). If you encounter any bugs or usage issues, please feel free to create an issue on [our issue tracker](https://github.com/Committable/Seraph/issues).*

## Quick Start

A container with required dependencies configured can be found [here](https://hub.docker.com/r/luongnguyen/oyente/). The image is however outdated. We are working on pushing the latest image to dockerhub for your convenience. If you experience any issue with this image, please try to build a new docker image by pulling this codebase before open an issue.

To open the container, install docker and run:

```
docker pull committable/tc-seraph && docker run -i -t committable/tc-seraph
```

To evaluate the greeter contract inside the container, run:

```
cd /oyente/oyente && python oyente.py -s greeter.sol
```

and you are done!

Note - If need the [version of Oyente](https://github.com/melonproject/oyente/tree/290f1ae1bbb295b8e61cbf0eed93dbde6f287e69) referred to in the paper, run the container from [here](https://hub.docker.com/r/hrishioa/oyente/)

To run the web interface, execute
`docker run -w /oyente/web -p 3000:3000 oyente:latest ./bin/rails server`

## Custom Docker image build

```
docker build -t seraph .
docker run -it -p 50051:50051 seraph:latest
```

## Installation

Execute a python virtualenv

```
python -m virtualenv env
source env/bin/activate
```

Install Seraph via pip:

```
$ pip3 install seraph
```

## Build 

### Install the following dependencies
#### python3
```
$ sudo apt-get install python3 pip3
```

#### module requirements
```
$ pip3 install -r rquiretments.txt
```

### Integration test

```

```

And that's it! Run ```python oyente.py --help``` for a list of options.


## Miscellaneous Utilities


## Benchmarks

Note: This is an improved version of the tool used for the paper. Benchmarks are not for direct comparison.

To run the benchmarks, it is best to use the docker container as it includes the blockchain snapshot necessary.
In the container, run `batch_run.py` after activating the virtualenv. Results are in `results.json` once the benchmark completes.

The benchmarks take a long time and a *lot* of RAM in any but the largest of clusters, beware.

Some analytics regarding the number of contracts tested, number of contracts analysed etc. is collected when running this benchmark.

## Contributing

Checkout out our [contribution guide](https://github.com/Committable/Seraph/blob/master/CONTRIBUTING.md) and the code structure [here](https://github.com/Committable/Seraph/blob/master/code.md).


[gitter-badge]: https://img.shields.io/gitter/room/melonproject/oyente.js.svg?style=flat-square
[gitter-url]: https://gitter.im/melonproject/oyente?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge
[license-badge]: https://img.shields.io/badge/License-GPL%20v3-blue.svg?style=flat-square
[license-badge-url]: ./LICENSE
