TAS-core(Trusted Analysis Service core)
======

An Implementation of ***Committable Transparent Center Analysis Service*** for solidity source file which gets two source files as input and produces their differences in form of graphs and abstractions of *ast/cfg/ssg*. 

[![License: GPL v3][license-badge]][license-badge-url]
[![Build Status](https://img.shields.io/github/workflow/status/Committable/TAS-core/Pytest)]()

*This repository is currently maintained by yangzq12 ([@yangzq12](https://github.com/yangzq12)). If you encounter any bugs or usage issues, please feel free to create an issue on [our issue tracker](https://github.com/Committable/TAS-core/issues).*

##  APIs for Committable Transparent Center Analysis Service

### Base Definitions of request and responds in proto:
1. Source code analysis service:
```
message AnalysisTarget{
    string repo_path = 1; // path to repo's project root directory
    string file_path = 2; // path to analyzing source code file
}

message SourceCodeAnalysisRequest{
    AnalysisTarget before_change= 1; // path to analysis target before change
    AnalysisTarget after_change = 2; // path to analysis target after change
    
    string diffs_log_path = 3; // path to difference file of the source code files
}

message SourceCodeAnalysisResponse{
    int32 status = 1;  // 200 for success
    string message = 2; // detailed message for the response
    string ast_before_path = 3; // path to ast.json of source code file before change
    string ast_after_path = 4; // path to ast.json of source code file after change

    string ast_abstract_path = 5; // path to ast_abstract.json

    string ast_edge_lists_before_path = 6; // path to ast_edges of source code file before change
    string ast_edge_lists_after_path = 7; // path to ast_edges of source code file after change
}
```
2. Bytecode analysis service:
```
message AnalysisTarget{
    string repo_path = 1; // path to repo's project root directory
    string file_path = 2; // path to analyzing source code file
}

message ByteCodeAnalysisRequest{
    AnalysisTarget before_change= 1; // path to analysis target before change
    AnalysisTarget after_change = 2; // path to analysis target after change
    
    string diffs_log_path = 3; // path to difference file of the source code files
}

message ByteCodeAnalysisResponse{
    int32 status = 1;
    string message = 2;

    string cfg_before_path = 3; //path to cfg.json of source code file before change, "" if not support
    string cfg_after_path = 4; //path to cfg.json of source code file before change, "" if not support

    string ssg_before_path = 5; //path to ssg.json of source code file before change, "" if not support
    string ssg_after_path = 6; //path to ssg.json of source code file before change, "" if not support

    string cfg_abstract_path = 7; 
    string ssg_abstract_path = 8;

    string cfg_edge_lists_before_path = 9;
    string cfg_edge_lists_after_path = 10;

    string ssg_edge_lists_before_path = 11;
    string ssg_edge_lists_after_path = 12;
}
```
### GRPC Services Definition in proto:

1. solidity service
```
service SoliditySourceCodeAnalysis{
    rpc AnalyseSourceCode(analyzer.SourceCodeAnalysisRequest) returns (analyzer.SourceCodeAnalysisResponse);
}
```
2. evm service
```
service EVMEngine{
    rpc AnalyseByteCode(analyzer.ByteCodeAnalysisRequest) returns (analyzer.ByteCodeAnalysisResponse);
}
```

<p id="1"></p>

## Quick Start

Containers of solidity-service and evm-service can be fined [here](https://hub.docker.com/u/dockeryangzq12). If you experience any issue with this image, please try to build a new docker image by pulling this codebase before open an issue.

To open the container, install docker and run:

solidity service
```
docker pull committable/solidity-analysis-docker
docker run -p 50054:50054 -v /path/to/test/repos:/repos -v /path/to/output/reports:/reports  solidity-analysis-docker
```
or evm service
```
docker pull committable/evm-analysis-docker
docker run -p 50055:50055 -v /path/to/test/repos:/repos -v /path/to/output/reports:/reports  evm-analysis-docker
```

To evaluate the service inside the container, run:

```
cd ./test/service_test_client
go build .
./service_test -input openzeppelin_master_commit_source.xlsx -type sol/evm -repos /path/to/test/repos -reports /path/to/output/reports -result /path/to/result

```

and you are done!

## Custom Docker image build

solidity service
```
docker build -f ./solidity_service/Dockerfile --cache-from=soliditybuilder --target soliditybuilder -t soliditybuilder .

docker build -f ./solidity_service/Dockerfile --build-arg BUILDKIT_INLINE_CACHE=1 --cache-from=soliditybuilder --cache-from=solidity-analysis-docker -t solidity-analysis-docker .
```

or evm service
```
docker build -f ./evm_service/Dockerfile --cache-from=evmbuilder --target evmbuilder -t evmbuilder .

docker build -f ./evm_service/Dockerfile --build-arg BUILDKIT_INLINE_CACHE=1 --cache-from=evmbuilder --cache-from=evm-analysis-docker -t evm-analysis-docker .
```

## Build and Test

Execute a python virtualenv

```
python -m virtualenv env
source env/bin/activate
```

Install the following dependencies

#### python3 & graphviz
```
$ sudo apt-get update
$ sudo apt-get install python3.6
$ sudo apt-get install graphviz-dev
```

#### python module requirements
```
$ pip3 install -r requiretments.txt
```

### Integration test

```
./run_evm.py
```
Or
```
./run_solidity.py
```

And that's it!


## Benchmarks
we selected commits from [Dapp-Learning](https://github.com/Dapp-Learning-DAO/Dapp-Learning) and [openzeppelin-contracts](https://github.com/OpenZeppelin/openzeppelin-contracts) repository as the benchmark.

To run the benchmarks, it is best to use the docker container and service_test as shown in [Quick Start](#1)


## Contributing

Checkout out our [contribution guide](https://github.com/Committable/TAS-core/blob/master/CONTRIBUTING.md).


[license-badge]: https://img.shields.io/github/license/Committable/TAS-core
[license-badge-url]: ./LICENSE
