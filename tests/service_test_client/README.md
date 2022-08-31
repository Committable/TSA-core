
run solidity service:
```
docker run -p 50054:50054 -v /home/liyue/transparentCenter/AnalysisService/service_test/test/repos:/repos -v /home/liyue/transparentCenter/AnalysisService/service_test/test/reports:/reports  solidity-analysis-docker /bin/bash
```
run evm service:
```
docker run -p 50055:50055 -v /home/liyue/transparentCenter/AnalysisService/service_test/test/repos:/repos -v /home/liyue/transparentCenter/AnalysisService/service_test/test/reports:/reports  evm-analysis-docker /bin/bash
```
run markdown service:
```
docker run -p 50057:50057 -v /home/liyue/transparentCenter/AnalysisService/service_test/test/repos:/repos -v /home/liyue/transparentCenter/AnalysisService/service_test/test/reports:/reports  md-analysis-docker /bin/bash
```
run go service:
```
docker run -p 50053:50053 -v /home/liyue/transparentCenter/AnalysisService/service_test/test/repos:/repos -v /home/liyue/transparentCenter/AnalysisService/service_test/test/reports:/reports  go-analysis-docker /bin/bash
```
run handler service:
```
docker run -p 50051:50051 -v /home/liyue/transparentCenter/AnalysisService/service_test/test/repos:/repos -v /home/liyue/transparentCenter/AnalysisService/service_test/test/reports:/reports  analysis-handler-docker /bin/bash
```
