import asyncio

import grpc
from protos.analyzer import move_analyzer_pb2_grpc
from protos.analyzer import source_code_analyzer_pb2

from analyzers.src_ast_analyzer.move_src import MoveAnalyzer
from utils import log, util

from services import service_base

cfg = util.get_config('./config.yaml')

log.mylogger = log.get_logger('move')


class MoveSourceCodeAnalysisService(
        move_analyzer_pb2_grpc.MoveSourceCodeAnalysisServicer):

    def AnalyseSourceCode(
            self, request: source_code_analyzer_pb2.SourceCodeAnalysisRequest,
            unused_context
    ) -> source_code_analyzer_pb2.SourceCodeAnalysisResponse:
        analyzer = MoveAnalyzer()
        return service_base.analysis_source_code(request, unused_context,
                                                 analyzer)


async def serve(address) -> None:
    server = grpc.aio.server()

    move_analyzer_pb2_grpc.add_MoveSourceCodeAnalysisServicer_to_server(  # pylint: disable=line-too-long
        MoveSourceCodeAnalysisService(), server)
    server.add_insecure_port(address)
    log.mylogger.info('Move Analysis Service is Listening on %s.', address)
    await server.start()
    await server.wait_for_termination()


if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(serve(cfg['listen_address']))
