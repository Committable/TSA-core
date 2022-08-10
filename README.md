Seraph
======

An ***Implementation*** of solidity source file analysis services satisfying self-defined APIs for ***Committable's Analysis Engine Services*** which gets two source files as input and produces their difference of graphs and abstraction of *ast/cfg/ssg*. 

[![Gitter][gitter-badge]][gitter-url]
[![License: GPL v3][license-badge]][license-badge-url]
[![Build Status](https://img.shields.io/github/workflow/status/Committable/AnalysisService/Analysis%20Handler%20Docker%20Build-Push)]()

*This repository is currently maintained by yangzq12 ([@yangzq12](https://github.com/yangzq12)). If you encounter any bugs or usage issues, please feel free to create an issue on [our issue tracker](https://github.com/Committable/Seraph/issues).*


## Committable's Analysis Engine Service APIs

### Base Definitions of request and responds in proto:
1. Source code analysis service:
```
message AnalysisTarget{
    string repo_path = 1; // absolute path to repo's project root directory
    string file_path = 2; // absolute path to analyzing source code file
}

message SourceCodeAnalysisRequest{
    AnalysisTarget before_change= 1; // absolute path to analysis target before change
    AnalysisTarget after_change = 2; // absolute path to analysis target after change
    
    string diffs_log_path = 3; // absolute path to difference file of the source code files
}

message SourceCodeAnalysisResponse{
    int32 status = 1;
    string message = 2;
    string ast_before_path = 3; //absolute path to ast.json of source code file before change
    string ast_after_path = 4; 

    string ast_abstract_path = 5;

    string ast_edge_lists_before_path = 6;
    string ast_edge_lists_after_path = 7; 
}
```
2. Bytecode analysis service:
```
message AnalysisTarget{
    string repo_path = 1; // absolute path to repo's project root directory
    string file_path = 2; // absolute path to analyzing source code file
}

message ByteCodeAnalysisRequest{
    AnalysisTarget before_change= 1; // absolute path to analysis target before change
    AnalysisTarget after_change = 2; // absolute path to analysis target after change
    
    string diffs_log_path = 3; // absolute path to difference file of the source code files
}

message ByteCodeAnalysisResponse{
    int32 status = 1;
    string message = 2;

    string cfg_before_path = 3; //absolute path to cfg.json of source code file before change, "" if not support
    string cfg_after_path = 4; //absolute path to cfg.json of source code file before change, "" if not support

    string ssg_before_path = 5; //absolute path to ssg.json of source code file before change, "" if not support
    string ssg_after_path = 6; //absolute path to ssg.json of source code file before change, "" if not support

    string cfg_abstract_path = 7; 
    string ssg_abstract_path = 8;

    string cfg_edge_lists_before_path = 9;
    string cfg_edge_lists_after_path = 10;

    string ssg_edge_lists_before_path = 11;
    string ssg_edge_lists_after_path = 12;
}
```
### GRPC Services Definition in proto

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

## Quick Start

Containers of solidity-service and evm-service can be fined [here](https://hub.docker.com/u/dockeryangzq12). If you experience any issue with this image, please try to build a new docker image by pulling this codebase before open an issue.

To open the container, install docker and run:

solidity service
```
docker pull committable/solidity-analysis-docker
docker run -p 50054:50054 -v /home/liyue/path/to/test/repos:/repos -v /path/to/output/reports:/reports  solidity-analysis-docker
```
or evm service
```
docker pull committable/evm-analysis-docker
docker run -p 50055:50055 -v /home/liyue/path/to/test/repos:/repos -v /path/to/output/reports:/reports  evm-analysis-docker
```

To evaluate the service inside the container, run:

```
cd /service_test
go build .
./service_test -type xlsx -input sol/evm
```

and you are done!

## Custom Docker image build

solidity service
```
docker build -f ./solidityService/Dockerfile --cache-from=soliditybuilder --target soliditybuilder -t soliditybuilder .

docker build -f ./solidityService/Dockerfile --build-arg BUILDKIT_INLINE_CACHE=1 --cache-from=soliditybuilder --cache-from=solidity-analysis-docker -t solidity-analysis-docker .
```

or evm service
```
docker build -f ./evmService/Dockerfile --cache-from=evmbuilder --target evmbuilder -t evmbuilder .

docker build -f ./evmService/Dockerfile --build-arg BUILDKIT_INLINE_CACHE=1 --cache-from=evmbuilder --cache-from=evm-analysis-docker -t evm-analysis-docker .
```

## Build and Test

Execute a python virtualenv

```
python -m virtualenv env
source env/bin/activate
```

Install the following dependencies

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
./run_evm.py
```
Or
```
./run_solidity.py
```

And that's it!

## Miscellaneous Utilities


## Benchmarks

Note: This is an improved version of the tool used for the paper. Benchmarks are not for direct comparison.

To run the benchmarks, it is best to use the docker container as it includes the blockchain snapshot necessary.
In the container, run `batch_run.py` after activating the virtualenv. Results are in `results.json` once the benchmark completes.

The benchmarks take a long time and a *lot* of RAM in any but the largest of clusters, beware.

Some analytics regarding the number of contracts tested, number of contracts analysed etc. is collected when running this benchmark.

## Contributing

Checkout out our [contribution guide](https://github.com/Committable/Seraph/blob/master/CONTRIBUTING.md) and the code structure [here](https://github.com/Committable/Seraph/blob/master/code.md).


[gitter-badge]: https://img.shields.io/gitter/room/yangzq11/seraph
[gitter-url]: https://gitter.im/yangzq12/seraph#
[license-badge]: https://img.shields.io/github/license/yangzq12/openzeppelin
[license-badge-url]: ./LICENSE
