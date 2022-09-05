This is go client implementation for sourcecode and bytecode analysis service.

## Usage
run solidity service:
```
docker run -p 50054:50054 -v /home/liyue/transparentCenter/Seraph/tests/service_test_client/workspace/repos:/repos -v /home/liyue/transparentCenter/Seraph/tests/service_test_client/workspace/reports:/reports  solidity-analysis-docker /bin/bash
```
run evm service:
```
docker run -p 50055:50055 -v /home/liyue/transparentCenter/Seraph/tests/service_test_client/workspace/repos:/repos -v /home/liyue/transparentCenter/Seraph/tests/service_test_client/workspace/reports:/reports  evm-analysis-docker /bin/bash
```
run markdown service:
```
docker run -p 50057:50057 -v /home/liyue/transparentCenter/Seraph/tests/service_test_client/worksapce/repos:/repos -v /home/liyue/transparentCenter/Seraph/tests/service_test_client/workspace/reports:/reports  md-analysis-docker /bin/bash
```
run go service:
```
docker run -p 50053:50053 -v /home/liyue/transparentCenter/Seraph/tests/service_test_client/workspace/repos:/repos -v /home/liyue/transparentCenter/Seraph/tests/service_test_client/workspace/reports:/reports  go-analysis-docker /bin/bash
```
run handler service:
```
docker run -p 50051:50051 -v /home/liyue/transparentCenter/Seraph/tests/service_test_client/worksapce/repos:/repos -v /home/liyue/transparentCenter/Seraph/tests/service_test_client/workspace/reports:/reports  analysis-handler-docker /bin/bash
```

./service_test -type sol -input xlsx