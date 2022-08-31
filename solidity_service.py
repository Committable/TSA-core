import asyncio
import json
import os
import time
import traceback

import grpc
from protos import analyzer as pb
import z3

import analyzer
import context
import global_params
import log
import utils

cfg = utils.get_config('./config.yaml')

global_params.DEST_PATH = cfg['dest_path']
global_params.INPUT_PATH = cfg['input_path']
global_params.SYM_TIMEOUT = cfg['timeout']
global_params.DEBUG_MOD = cfg['debug']

log.mylogger = log.get_logger('solidity')


class SoliditySourceCodeAnalysisService(
        pb.solidity_analyzer_pb2_grpc.SoliditySourceCodeAnalysisServicer):

    def AnalyseSourceCode(
        self, request: pb.source_code_analyzer_pb2.SourceCodeAnalysisRequest,
        unused_context
    ) -> pb.source_code_analyzer_pb2.SourceCodeAnalysisResponse:
        start = time.time()
        request_id = str(int(start * 1000000))
        output_path = utils.generate_output_dir(request_id, 'source_before')
        src_path = request.before_change.file_path
        project_path = os.path.join(
            global_params.INPUT_PATH,
            utils.change_to_relative(request.before_change.repo_path))
        diff_path = os.path.join(
            global_params.INPUT_PATH,
            utils.change_to_relative(request.diffs_log_path))

        log.mylogger.info(
            'starting process  request %s for commit before, '
            'project: %s, file: %s', request_id, project_path, src_path)
        diff = utils.get_diff(diff_path, True)
        context_before = context.Context(start, project_path, src_path, diff,
                                         '', request_id)
        try:
            report_b = analyzer.analyze_solidity_code(output_path, src_path,
                                                      project_path,
                                                      context_before)
        except Exception as err:  # pylint: disable=broad-except
            traceback.print_exc()
            log.mylogger.error(
                'fail analyzing sol source file before for %s, err: %s',
                src_path, str(err))
            return pb.source_code_analyzer_pb2.SourceCodeAnalysisResponse(
                status=500, message='analysis sol before file fail')

        output_path = utils.generate_output_dir(request_id, 'source_after')
        src_path = request.after_change.file_path
        project_path = os.path.join(
            global_params.INPUT_PATH,
            utils.change_to_relative(request.after_change.repo_path))
        log.mylogger.info(
            'starting process request %s for commit after, '
            'project: %s, file: %s', request_id, project_path, src_path)

        diff = utils.get_diff(diff_path, False)
        context_after = context.Context(start, project_path, src_path, diff, '',
                                        request_id)
        try:
            report_a = analyzer.analyze_solidity_code(output_path, src_path,
                                                      project_path,
                                                      context_after)
        except Exception as err:  # pylint: disable=broad-except
            traceback.print_exc()
            log.mylogger.error(
                'fail analyzing sol source file after for %s, err: %s',
                output_path, str(err))
            return pb.source_code_analyzer_pb2.SourceCodeAnalysisResponse(
                status=500, message='analysis sol after file fail')
        # merge before's and after's abstarct
        try:
            output_path = utils.generate_output_dir(request_id, '')
            ast_abstract = {}
            for index in report_a.ast_abstract:
                if not context_before.err and not context_after.err:
                    ast_abstract[index] = report_a.ast_abstract[
                        index] - report_b.ast_abstract[index]
                else:
                    ast_abstract[index] = 0
            ast_abstract_path = os.path.join(output_path, 'ast_abstract.json')
            with open(ast_abstract_path, 'w', encoding='utf8') as output_file:
                json.dump(ast_abstract, output_file)
        except Exception as err:  # pylint: disable=broad-except
            traceback.print_exc()
            log.mylogger.error('merge ast abstract err: %s', str(err))
            return pb.source_code_analyzer_pb2.SourceCodeAnalysisResponse(
                status=500, message='merge ast abstract file fail')

        log.mylogger.info('success analyzing request: %s, result in %s ',
                          request_id, output_path)
        return pb.source_code_analyzer_pb2.SourceCodeAnalysisResponse(
            status=200,
            message='solidity analysis result',
            ast_before_path=utils.change_to_relative(
                utils.remove_prefix(report_b.ast_json_path,
                                    global_params.DEST_PATH)),
            ast_after_path=utils.change_to_relative(
                utils.remove_prefix(report_a.ast_json_path,
                                    global_params.DEST_PATH)),
            ast_abstract_path=utils.change_to_relative(
                utils.remove_prefix(ast_abstract_path,
                                    global_params.DEST_PATH)),
            ast_edge_lists_before_path=utils.change_to_relative(
                utils.remove_prefix(report_b.ast_edge_list_path,
                                    global_params.DEST_PATH)),
            ast_edge_lists_after_path=utils.change_to_relative(
                utils.remove_prefix(report_a.ast_edge_list_path,
                                    global_params.DEST_PATH)))


async def serve(address) -> None:
    server = grpc.aio.server()
    pb.solidity_analyzer_pb2_grpc.add_SoliditySourceCodeAnalysisServicer_to_server(  # pylint: disable=line-too-long
        SoliditySourceCodeAnalysisService(), server)
    server.add_insecure_port(address)
    log.mylogger.info('Solidity Analysis Serverice is Listening on %s.',
                      address)
    await server.start()
    await server.wait_for_termination()


# TODO(Chao): Check EVM, EMCC, Golang, and Solc as well
def has_dependencies_installed(evm=False, emcc=False, golang=False, solc=False):
    try:
        del evm, emcc, golang, solc  # Unused, reserve for name hint
        z3_version = z3.get_version_string()
        tested_z3_version = '4.8.12'
        if utils.compare_versions(z3_version, tested_z3_version) > 0:
            log.mylogger.debug(
                'You are using an untested version of z3. '
                '%s is the officially tested version', tested_z3_version)
    except:  # pylint: disable=bare-except
        log.mylogger.critical('Z3 is not available. Please install z3 from '
                              'https://github.com/Z3Prover/z3.')
        return False


if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(serve(cfg['listen_address']))
