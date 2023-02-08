import asyncio
import json
import os
import time
import traceback

import grpc
from protos.analyzer import solidity_analyzer_pb2_grpc
from protos.analyzer import source_code_analyzer_pb2
import z3

import analyzer
from utils import global_params, context, log, util

cfg = util.get_config('./config.yaml')

global_params.DEST_PATH = cfg['dest_path']
global_params.INPUT_PATH = cfg['input_path']
global_params.SYM_TIMEOUT = cfg['timeout']
global_params.DEBUG_MOD = cfg['debug']

log.mylogger = log.get_logger('solidity')


class SoliditySourceCodeAnalysisService(
        solidity_analyzer_pb2_grpc.SoliditySourceCodeAnalysisServicer):

    def AnalyseSourceCode(
            self, request: source_code_analyzer_pb2.SourceCodeAnalysisRequest,
            unused_context
    ) -> source_code_analyzer_pb2.SourceCodeAnalysisResponse:
        start = time.time()
        request_id = str(int(start * 1000000))
        project_name = "Default"
        output_path = util.generate_output_dir('sol_source_before', request_id)
        src_path = request.before_change.file_path
        project_path = os.path.join(
            global_params.INPUT_PATH,
            util.change_to_relative(request.before_change.repo_path))
        diff_path = os.path.join(
            global_params.INPUT_PATH,
            util.change_to_relative(request.diffs_log_path))

        log.mylogger.info(
            'starting process  request %s for commit before, '
            'project: %s, file: %s', request_id, project_path, src_path)
        diff = util.get_diff(diff_path, True)
        context_before = context.Context(start, project_path, src_path, diff,
                                         '', request_id)
        try:
            report_b = analyzer.analyze_solidity_code_from_antlr(output_path, src_path,
                                                      project_path,
                                                      context_before,
                                                      cfg['compilation'][project_name])
        except Exception as err:  # pylint: disable=broad-except
            traceback.print_exc()
            log.mylogger.error(
                'fail analyzing sol source file before for %s, err: %s',
                src_path, str(err))
            return source_code_analyzer_pb2.SourceCodeAnalysisResponse(
                status=500, message='analysis sol before file fail')

        output_path = util.generate_output_dir('sol_source_after', request_id)
        src_path = request.after_change.file_path
        project_path = os.path.join(
            global_params.INPUT_PATH,
            util.change_to_relative(request.after_change.repo_path))
        log.mylogger.info(
            'starting process request %s for commit after, '
            'project: %s, file: %s', request_id, project_path, src_path)

        diff = util.get_diff(diff_path, False)
        context_after = context.Context(start, project_path, src_path, diff, '',
                                        request_id)
        try:
            report_a = analyzer.analyze_solidity_code_from_antlr(output_path, src_path,
                                                      project_path,
                                                      context_after,
                                                      cfg['compilation'][project_name])
        except Exception as err:  # pylint: disable=broad-except
            log.mylogger.error(
                'fail analyzing sol source file after for %s, err: %s',
                output_path, str(err))
            return source_code_analyzer_pb2.SourceCodeAnalysisResponse(
                status=500, message='analysis sol after file fail')
        # merge before's and after's abstarct
        try:
            output_path = util.generate_output_dir('sol_ast_abstract', request_id)
            ast_abstract = {}
            for index in report_a.ast_abstract:
                # todo: if we analyse before or after fail, e.g. complie fail..., we ignore changes
                if not context_before.err and not context_after.err:
                    ast_abstract[index] = report_a.ast_abstract[
                        index] - report_b.ast_abstract[index]
                else:
                    ast_abstract[index] = 0
            ast_abstract_path = os.path.join(output_path, 'ast_abstract.json')
            with open(ast_abstract_path, 'w', encoding='utf8') as output_file:
                json.dump(ast_abstract, output_file)
        except Exception as err:  # pylint: disable=broad-except
            log.mylogger.error('merge ast abstract err: %s', str(err))
            return source_code_analyzer_pb2.SourceCodeAnalysisResponse(
                status=500, message='merge ast abstract file fail')

        log.mylogger.info('success analyzing request: %s, result in %s ',
                          request_id, output_path)
        return source_code_analyzer_pb2.SourceCodeAnalysisResponse(
            status=200,
            message='solidity analysis result',
            ast_before_path=util.change_to_relative(
                util.remove_prefix(report_b.ast_json_path,
                                   global_params.DEST_PATH)),
            ast_after_path=util.change_to_relative(
                util.remove_prefix(report_a.ast_json_path,
                                   global_params.DEST_PATH)),
            ast_abstract_path=util.change_to_relative(
                util.remove_prefix(ast_abstract_path, global_params.DEST_PATH)),
            ast_edge_lists_before_path=util.change_to_relative(
                util.remove_prefix(report_b.ast_edge_list_path,
                                   global_params.DEST_PATH)),
            ast_edge_lists_after_path=util.change_to_relative(
                util.remove_prefix(report_a.ast_edge_list_path,
                                   global_params.DEST_PATH)))


async def serve(address) -> None:
    server = grpc.aio.server()
    solidity_analyzer_pb2_grpc.add_SoliditySourceCodeAnalysisServicer_to_server(  # pylint: disable=line-too-long
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
        if util.compare_versions(z3_version, tested_z3_version) > 0:
            log.mylogger.debug(
                'You are using an untested version of z3. '
                '%s is the officially tested version', tested_z3_version)
    except:  # pylint: disable=bare-except
        log.mylogger.critical('Z3 is not available. Please install z3 from '
                              'https://github.com/Z3Prover/z3.')
        return False


if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(serve(cfg['listen_address']))
