This is go client implementation for sourcecode and bytecode analysis service.

## Usage
run solidity service:
```
docker run -p 50054:50054 -v /path/to/repos:/repos -v /path/to/reports:/reports  solidity-analysis-docker /bin/bash
```
run evm service:
```
docker run -p 50055:50055 -v /path/to/repos:/repos -v /path/to/reports:/reports  evm-analysis-docker /bin/bash
```
run markdown service:
```
docker run -p 50057:50057 -v /path/to/repos:/repos -v/path/to/reports:/reports  md-analysis-docker /bin/bash
```
run go service:
```
docker run -p 50053:50053 -v /path/to/repos:/repos -v /path/to/reports:/reports  go-analysis-docker /bin/bash
```
run handler service:
```
docker run -p 50051:50051 -v /path/to/repos:/repos -v /path/to/reports:/reports  analysis-handler-docker /bin/bash
```

./service_test -input openzeppelin_master_commit_source.xlsx -type sol/evm -repos /path/to/test/repos -reports /path/to/output/reports -result /path/to/result
