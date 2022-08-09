import os
import grpc
import asyncio
import log
import global_params
import time
import json
import traceback
import threading

from protos.analyzer import bytecode_analyzer_pb2, evm_engine_pb2_grpc
from utils import get_config, generate_output_dir, change_to_relative, remove_prefix, get_diff
from analyzer import analyze_evm_from_solidity
from context import Context

cfg = get_config("./config.yaml")

global_params.DEST_PATH = cfg["dest_path"]
global_params.INPUT_PATH = cfg["input_path"]
global_params.SYM_TIMEOUT = cfg["timeout"]
global_params.DEBUG_MOD = cfg["debug"]

log.mylogger = log.get_logger("evm")
# todo: z3-solver will error if concurrently processing calls for EvmEngineService
lock = threading.Lock()


class EvmEngineService(evm_engine_pb2_grpc.EVMEngineServicer):
    def AnalyseByteCode(self, request: bytecode_analyzer_pb2.ByteCodeAnalysisRequest,
                        unused_context) -> bytecode_analyzer_pb2.ByteCodeAnalysisResponse:
        request_id = str(int(time.time() * 1000000))
        log.mylogger.info("waiting for request %s, project: %s, file: %s", request_id, request.before_change.repo_path,
                          request.before_change.file_path)
        # wait for other request end
        lock.acquire()
        # start processing request
        # 1. before commit, i.e. parent
        start = time.time()

        output_path = generate_output_dir(request_id, "bytecode_before")
        src_path = request.before_change.file_path
        project_path = os.path.join(global_params.INPUT_PATH, change_to_relative(request.before_change.repo_path))
        diff_path = os.path.join(global_params.INPUT_PATH, change_to_relative(request.diffs_log_path))
        log.mylogger.info("starting process request %s for commit before, project: %s, file: %s",
                          request_id, project_path, src_path)

        diff = get_diff(diff_path, True)
        context_before = Context(start, project_path, src_path, diff, "", request_id)
        try:
            cfg_b, ssg_b = analyze_evm_from_solidity(output_path, src_path, project_path, context_before)
        except Exception as err:
            traceback.print_exc()
            context_before.set_err()
            log.mylogger.error("fail analyzing evm bytecode before for %s, err: %s", src_path, str(err))
            lock.release()
            return bytecode_analyzer_pb2.ByteCodeAnalysisResponse(status=500, message="analysis evm before file error")

        # 2. after commit, i.e. child
        start = time.time()
        output_path = generate_output_dir(request_id, "bytecode_after")
        src_path = request.after_change.file_path
        project_path = os.path.join(global_params.INPUT_PATH, change_to_relative(request.after_change.repo_path))
        log.mylogger.info("starting processing request %s for commit after, project: %s, file: %s",
                          request_id, project_path, src_path)
        diff = get_diff(diff_path, False)
        context_after = Context(start, project_path, src_path, diff, "", request_id)
        try:
            cfg_a, ssg_a = analyze_evm_from_solidity(output_path, src_path, project_path, context_after)
        except Exception as err:
            traceback.print_exc()
            context_after.set_err()
            log.mylogger.error("fail analyzing evm bytecode after for %s, err: %s", output_path, str(err))
            lock.release()
            return bytecode_analyzer_pb2.ByteCodeAnalysisResponse(status=500, message="analysis evm after file error")

        # merge before's and after's cfg abstarct
        try:
            output_path = generate_output_dir(request_id, "")
            cfg_abstract = {}
            for index in cfg_a.cfg_abstract:
                if not context_before.err and not context_after.err:
                    cfg_abstract[index] = cfg_a.cfg_abstract[index] - cfg_b.cfg_abstract[index]
                else:
                    cfg_abstract[index] = 0
            cfg_abstract_path = os.path.join(output_path, "cfg_abstract.json")
            with open(cfg_abstract_path, 'w') as output_file:
                json.dump(cfg_abstract, output_file)
        except Exception as err:
            traceback.print_exc()
            log.mylogger.error("fail merge cfg abstract, err: %s", str(err))
            lock.release()
            return bytecode_analyzer_pb2.ByteCodeAnalysisResponse(status=500,
                                                                  message="merge cfg abstract fail")

        # merge before's and after's ssg abstarct
        try:
            output_path = generate_output_dir(request_id, "")
            ssg_abstract = {}
            for index in ssg_a.ssg_abstract:
                if not context_before.err and not context_after.err:
                    ssg_abstract[index] = ssg_a.ssg_abstract[index] - ssg_b.ssg_abstract[index]
                else:
                    ssg_abstract[index] = 0
            ssg_abstract_path = os.path.join(output_path, "ssg_abstract.json")
            with open(ssg_abstract_path, 'w') as output_file:
                json.dump(ssg_abstract, output_file)
        except Exception as err:
            traceback.print_exc()
            log.mylogger.error("fail merge ssg abstract, err: %s", str(err))
            lock.release()
            return bytecode_analyzer_pb2.ByteCodeAnalysisResponse(status=500,
                                                                  message="merge ssg abstract fail")

        log.mylogger.info("success analyzing request %s, result in %s ", request_id, output_path)
        lock.release()
        return bytecode_analyzer_pb2.ByteCodeAnalysisResponse(status=200,
                                                              message="solidity analysis result",
                                                              cfg_before_path=change_to_relative(
                                                                  remove_prefix(cfg_b.cfg_json_path,
                                                                                global_params.DEST_PATH)),
                                                              cfg_after_path=change_to_relative(
                                                                  remove_prefix(cfg_a.cfg_json_path,
                                                                                global_params.DEST_PATH)),

                                                              ssg_before_path=change_to_relative(
                                                                  remove_prefix(ssg_b.ssg_json_path,
                                                                                global_params.DEST_PATH)),
                                                              ssg_after_path=change_to_relative(
                                                                  remove_prefix(ssg_a.ssg_json_path,
                                                                                global_params.DEST_PATH)),

                                                              cfg_abstract_path=change_to_relative(
                                                                  remove_prefix(cfg_abstract_path,
                                                                                global_params.DEST_PATH)),
                                                              ssg_abstract_path=change_to_relative(
                                                                  remove_prefix(ssg_abstract_path,
                                                                                global_params.DEST_PATH)),

                                                              cfg_edge_lists_before_path=change_to_relative(
                                                                  remove_prefix(cfg_b.cfg_edge_lists_path,
                                                                                global_params.DEST_PATH)),
                                                              cfg_edge_lists_after_path=change_to_relative(
                                                                  remove_prefix(cfg_a.cfg_edge_lists_path,
                                                                                global_params.DEST_PATH)),

                                                              ssg_edge_lists_before_path=change_to_relative(
                                                                  remove_prefix(ssg_b.ssg_edge_lists_path,
                                                                                global_params.DEST_PATH)),
                                                              ssg_edge_lists_after_path=change_to_relative(
                                                                  remove_prefix(ssg_a.ssg_edge_lists_path,
                                                                                global_params.DEST_PATH)),
                                                              )


async def serve(address) -> None:
    server = grpc.aio.server()
    evm_engine_pb2_grpc.add_EVMEngineServicer_to_server(
        EvmEngineService(), server)
    server.add_insecure_port(address)
    log.mylogger.info("EVM Engine Service is Listening on %s...", address)

    await server.start()
    await server.wait_for_termination()


if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(serve(cfg["listen_address"]))
