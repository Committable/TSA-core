import asyncio

import grpc
from protos.analyzer import solidity_analyzer_pb2_grpc
from protos.analyzer import source_code_analyzer_pb2

from analyzers import solidity_src_antlr as analyzer
from utils import log, util
import service_base

cfg = util.get_config('./config.yaml')

log.mylogger = log.get_logger('solidity')


class SoliditySourceCodeAnalysisService(
        solidity_analyzer_pb2_grpc.SoliditySourceCodeAnalysisServicer):

    def AnalyseSourceCode(
            self, request: source_code_analyzer_pb2.SourceCodeAnalysisRequest,
            unused_context
    ) -> source_code_analyzer_pb2.SourceCodeAnalysisResponse:
        service_base.analysis_source_code(request, unused_context, analyzer.analyze_solidity_code_from_antlr)


async def serve(address) -> None:
    server = grpc.aio.server()
    solidity_analyzer_pb2_grpc.add_SoliditySourceCodeAnalysisServicer_to_server(  # pylint: disable=line-too-long
        SoliditySourceCodeAnalysisService(), server)
    server.add_insecure_port(address)
    log.mylogger.info('Solidity Analysis Serverice is Listening on %s.',
                      address)
    await server.start()
    await server.wait_for_termination()


if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(serve(cfg['listen_address']))
