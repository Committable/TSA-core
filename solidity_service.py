import grpc
import asyncio
import log
import time
import sys
import os
import json
import global_params
import traceback

from protos.analyzer import solidity_analyzer_pb2_grpc, source_code_analyzer_pb2
from utils import compare_versions, generate_output_dir, get_config, change_to_relative, remove_prefix, get_diff
from analyzer import analyze_solidity_code
from context import Context

cfg = get_config("./config.yaml")

global_params.DEST_PATH = cfg["dest_path"]
global_params.INPUT_PATH = cfg["input_path"]
global_params.SYM_TIMEOUT = cfg["timeout"]
global_params.DEBUG_MOD = cfg["debug"]

log.mylogger = log.get_logger("solidity")


class SoliditySourceCodeAnalysisService(solidity_analyzer_pb2_grpc.SoliditySourceCodeAnalysisServicer):
    def AnalyseSourceCode(self, request: source_code_analyzer_pb2.SourceCodeAnalysisRequest,
                          unused_context) -> source_code_analyzer_pb2.SourceCodeAnalysisResponse:
        start = time.time()
        request_id = str(int(start*1000000))
        output_path = generate_output_dir(request_id, "source_before")
        src_path = request.before_change.file_path
        project_path = os.path.join(global_params.INPUT_PATH, change_to_relative(request.before_change.repo_path))
        diff_path = os.path.join(global_params.INPUT_PATH, change_to_relative(request.diffs_log_path))

        log.mylogger.info("starting process  request %s for commit before, project: %s, file: %s",
                          request_id, project_path, src_path)
        diff = get_diff(diff_path, True)
        context_before = Context(start, project_path, src_path, diff, "", request_id)
        try:
            report_b = analyze_solidity_code(output_path, src_path, project_path, context_before)
        except Exception as err:
            traceback.print_exc()
            log.mylogger.error("fail analyzing sol source file before for %s, err: %s", src_path, str(err))
            return source_code_analyzer_pb2.SourceCodeAnalysisResponse(status=500,
                                                                       message="analysis sol before file fail")

        output_path = generate_output_dir(request_id, "source_after")
        src_path = request.after_change.file_path
        project_path = os.path.join(global_params.INPUT_PATH, change_to_relative(request.after_change.repo_path))
        log.mylogger.info("starting process request %s for commit after, project: %s, file: %s",
                          request_id, project_path, src_path)

        diff = get_diff(diff_path, False)
        context_after = Context(start, project_path, src_path, diff, "", request_id)
        try:
            report_a = analyze_solidity_code(output_path, src_path, project_path, context_after)
        except Exception as err:
            traceback.print_exc()
            log.mylogger.error("fail analyzing sol source file after for %s, err: %s", output_path, str(err))
            return source_code_analyzer_pb2.SourceCodeAnalysisResponse(status=500,
                                                                       message="analysis sol after file fail")
        # merge before's and after's abstarct
        ast_abstract_path = ""
        # try:
        #     output_path = generate_output_dir(request_id, "")
        #     ast_abstract = {}
        #     for index in report_a.ast_abstract:
        #         if not context_before.err and not context_after.err:
        #             ast_abstract[index] = report_a.ast_abstract[index] - report_b.ast_abstract[index]
        #         else:
        #             ast_abstract[index] = 0
        #     ast_abstract_path = os.path.join(output_path, "ast_abstract.json")
        #     with open(ast_abstract_path, 'w') as output_file:
        #         json.dump(ast_abstract, output_file)
        # except Exception as err:
        #     traceback.print_exc()
        #     log.mylogger.error("merge ast abstract err: %s", str(err))
        #     return source_code_analyzer_pb2.SourceCodeAnalysisResponse(status=500,
        #                                                                message="merge ast abstract file fail")

        log.mylogger.info("success analyzing request: %s, result in %s ", request_id, output_path)
        return source_code_analyzer_pb2.SourceCodeAnalysisResponse(status=200,
                                                                   message="solidity analysis result",
                                                                   ast_before_path=change_to_relative(
                                                                       remove_prefix(report_b.ast_json_path,
                                                                                     global_params.DEST_PATH)),
                                                                   ast_after_path=change_to_relative(
                                                                       remove_prefix(report_a.ast_json_path,
                                                                                     global_params.DEST_PATH)),
                                                                   ast_abstract_path=change_to_relative(
                                                                       remove_prefix(ast_abstract_path,
                                                                                     global_params.DEST_PATH)),
                                                                   ast_edge_lists_before_path=change_to_relative(
                                                                       remove_prefix(report_b.ast_edge_list_path,
                                                                                     global_params.DEST_PATH)),
                                                                   ast_edge_lists_after_path=change_to_relative(
                                                                       remove_prefix(report_a.ast_edge_list_path,
                                                                                     global_params.DEST_PATH)))


async def serve(address) -> None:
    server = grpc.aio.server()
    solidity_analyzer_pb2_grpc.add_SoliditySourceCodeAnalysisServicer_to_server(
        SoliditySourceCodeAnalysisService(), server)
    server.add_insecure_port(address)
    log.mylogger.info("Solidity Analysis Serverice is Listening on %s.", address)
    await server.start()
    await server.wait_for_termination()


def has_dependencies_installed(evm=False, emcc=False, golang=False, solc=False):
    try:
        import z3
        import z3.z3util
        z3_version = z3.get_version_string()
        tested_z3_version = '4.8.12'
        if compare_versions(z3_version, tested_z3_version) > 0:
            log.mylogger.debug(
                "You are using an untested version of z3. %s is the officially tested version" % tested_z3_version)
    except:
        log.mylogger.critical("Z3 is not available. Please install z3 from https://github.com/Z3Prover/z3.")
        return False


if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(serve(cfg["listen_address"]))
