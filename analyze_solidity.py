import logging
import traceback

from runtime.evmRuntime import EvmRuntime
from interpreter.evmInterpreter import EVMInterpreter
from inputDealer.soliditySourceMap import SourceMap
from inputDealer.inputHelper import InputHelper
from reporter.print_graph import *
from reporter.reporter import Reporter
import global_params

logger = logging.getLogger(__name__)


def analyze_solidity_code():
    exit_code = 100

    # 1. prepare input
    helper = InputHelper(global_params.SOLIDITY,
                         source=global_params.SRC_DIR,
                         joker=global_params.SRC_FILE,
                         compilation_err=global_params.COMPILATION_ERR)
    try:
        inputs = helper.get_solidity_inputs()
    except Exception as err:
        logger.exception(err)
        return 103

    if global_params.SRC_FILE in SourceMap.sources:
        report = Reporter(SourceMap.sources[global_params.SRC_FILE].get_content())
    else:
        report = Reporter("")
    global_params.REPORT = report

    if not global_params.IS_BEFORE:
        report.new_lines = len(global_params.DIFFS)

    if SourceMap.ast_helper is not None:
        report.get_structure_src(SourceMap.ast_helper.get_ast(global_params.SRC_FILE),
                                 SourceMap.ast_helper.get_source(global_params.SRC_FILE))
    # 2. get ast graph
    if SourceMap.ast_helper:
        ast_json = SourceMap.ast_helper.get_ast_report(global_params.SRC_FILE)
    else:
        ast_json = {"nodes": [], "edges": []}
    report.set_ast(ast_json)

    report.dump_ast()
    report.dump_ast_edge_list()

    #  There may be over one contracts in the solidity file and one contract correspones to one graph each
    for inp in inputs:
        logger.info("begin analysing contract: %s:", inp['contract'])
        # cfg = nx.DiGraph()
        env = EvmRuntime(platform=global_params.PLATFORM,
                         disasm_file=inp['disasm_file'],
                         source_map=inp['source_map'],
                         source_file=inp["source"]+os.sep+inp["joker"],
                         input_type=global_params.SOLIDITY,
                         evm=inp['evm'])
        try:
            env.build_cfg()
        except Exception as err:
            logger.exception("fail to build cfg for %s, err: %s", inp["contract"], str(err))
            return 104
        interpreter = EVMInterpreter(env, inp["contract"])
        try:
            return_code = interpreter.sym_exec()
            if len(interpreter.graphs) == 0:
                interpreter.graphs["all"] = interpreter.graph.get_graph()
            pass
        except Exception as err:
            logger.error("fail to symbolic execute for %s, err: %s", inp["contract"], str(err))
            traceback.print_exc()
            return 105
        # add cfg
        report.add_cfg(inp["contract"], env)
        # add ssg
        ssg_graph = interpreter.graphs
        report.add_ssg_new(inp["contract"], ssg_graph)
        report.print_coverage_info(inp["contract"], env, interpreter)
        logger.info("End analysing contract %s", inp["contract"])

    report.dump_cfg()
    report.dump_cfg_edge_list()

    report.dump_ssg()
    report.dump_ssg_edge_list()

    report.get_structure_bin()
    report.get_sementic_new()
    report.dump_meta_commit()

    if global_params.PRINT_GRAPH:
        report.print_ast_graph()
        report.print_cfg_graph()
        report.print_ssg_graph_new()

    return exit_code
