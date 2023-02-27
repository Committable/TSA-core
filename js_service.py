import asyncio
import json
import os
import time
import traceback

import grpc
from protos.analyzer import js_analyzer_pb2_grpc
from protos.analyzer import source_code_analyzer_pb2

from analyzers import js_src as analyzer
from utils import global_params, context, log, util

cfg = util.get_config('./config.yaml')

if 'dest_path' in cfg:
    global_params.DEST_PATH = cfg['dest_path']
if 'input_path' in cfg:
    global_params.INPUT_PATH = cfg['input_path']
if 'timeout' in cfg:
    global_params.SYM_TIMEOUT = cfg['timeout']
if 'debug' in cfg:
    global_params.DEBUG_MOD = cfg['debug']
if 'ast_abstracts' in cfg:
    global_params.AST = cfg['ast_abstracts']
if 'cfg_abstracts' in cfg:
    global_params.CFG = cfg['cfg_abstracts']
if 'ssg_abstracts' in cfg:
    global_params.AST = cfg['ssg_abstracts']

log.mylogger = log.get_logger('solidity')


class JsSourceCodeAnalysisService(
    js_analyzer_pb2_grpc.JsSourceCodeAnalysisServicer):

    def AnalyseSourceCode(
            self, request: source_code_analyzer_pb2.SourceCodeAnalysisRequest,
            unused_context
    ) -> source_code_analyzer_pb2.SourceCodeAnalysisResponse:
        start = time.time()
        request_id = str(int(start * 1000000))
        output_path = util.generate_output_dir('js_source_before', request_id)
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
        context_before = context.Context(start, project_path, src_path, diff, request_id,
                                         ast_abstracts=global_params.AST)
        try:
            report_b = analyzer.analyze_js_code_from_treesitter(output_path,
                                                                src_path,
                                                                project_path,
                                                                context_before)
        except Exception as err:  # pylint: disable=broad-except
            traceback.print_exc()
            log.mylogger.error(
                'fail analyzing js source file before for %s, err: %s',
                src_path, str(err))
            return source_code_analyzer_pb2.SourceCodeAnalysisResponse(
                status=500, message='analysis js before file fail')

        output_path = util.generate_output_dir('js_source_after', request_id)
        src_path = request.after_change.file_path
        project_path = os.path.join(
            global_params.INPUT_PATH,
            util.change_to_relative(request.after_change.repo_path))
        log.mylogger.info(
            'starting process request %s for commit after, '
            'project: %s, file: %s', request_id, project_path, src_path)

        diff = util.get_diff(diff_path, False)
        context_after = context.Context(start, project_path, src_path, diff, request_id,
                                        ast_abstracts=global_params.AST)
        try:
            report_a = analyzer.analyze_js_code_from_treesitter(output_path, src_path,
                                                                project_path,
                                                                context_after)
        except Exception as err:  # pylint: disable=broad-except
            log.mylogger.error(
                'fail analyzing js source file after for %s, err: %s',
                output_path, str(err))
            return source_code_analyzer_pb2.SourceCodeAnalysisResponse(
                status=500, message='analysis js after file fail')
        # merge before's and after's abstarct
        try:
            output_path = util.generate_output_dir('js_ast_abstract', request_id)
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
            message='javascript analysis result',
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

    js_analyzer_pb2_grpc.add_JsSourceCodeAnalysisServicer_to_server(  # pylint: disable=line-too-long
        JsSourceCodeAnalysisService(), server)
    server.add_insecure_port(address)
    log.mylogger.info('Javascript Analysis Serverice is Listening on %s.',
                      address)
    await server.start()
    await server.wait_for_termination()


if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(serve(cfg['listen_address']))
