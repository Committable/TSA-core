import logging


from runtime.evmRuntime import EvmRuntime
from interpreter.evmInterpreter import EVMInterpreter
from inputDealer.soliditySourceMap import SourceMap
from inputDealer.inputHelper import InputHelper
from reporter.print_graph import *
from reporter.reporter import Reporter

logger = logging.getLogger(__name__)


def analyze_solidity_code():
    exit_code = 100
    # 0. file not exist means file not created in this commit and it's a normal condition
    source_dir = global_params.SRC_DIR
    file_path = global_params.SRC_DIR + os.sep + global_params.SRC_FILE
    if not os.path.exists(source_dir) or not os.path.exists(file_path):
        ast = nx.DiGraph()
        cfg = nx.DiGraph()
        ssg = nx.DiGraph()
        print_ast_nx_graph(ast, file_name="ast")
        print_cfg_nx_graph(cfg, file_name="cfg")
        print_ssg_nx_graph(ssg, file_name="ssg")

        with open(os.path.join(global_params.DEST_PATH, "ast.json"), 'w') as outputfile:
            json.dump({"nodes": [], "edges": []}, outputfile)

        return 101

    # 1. prepare input
    helper = InputHelper(global_params.SOLIDITY,
                         source=global_params.SRC_DIR,
                         joker=global_params.SRC_FILE,
                         compilation_err=global_params.COMPILATION_ERR)
    try:
        inputs = helper.get_solidity_inputs()
    except Exception as err:
        logger.error(str(err))
        return 103

    report = Reporter(SourceMap.sources[global_params.SRC_FILE].get_content())
    # 2. get ast graph
    ast_json = SourceMap.ast_helper.get_ast_report(global_params.SRC_FILE)
    report.set_ast(ast_json)

    report.dump_ast()
    report.print_ast_graph()
    report.dump_ast_edge_list()

    #  There may be over one contracts in the solidity file and one contract correspones to one graph each
    for inp in inputs:
        logger.info("contract %s:", inp['contract'])
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
            logger.error("fail to build cfg for %s, err: %s", inp["contract"], str(err))
            return 104
        interpreter = EVMInterpreter(env)
        try:
            return_code = interpreter.sym_exec()
        except Exception as err:
            logger.error("fail to symbolic execute for %s, err: %s", inp["contract"], str(err))
            return 105
        logger.info("contract %s: %s", inp["contract"], str(interpreter.total_no_of_paths))

        # add cfg
        report.add_cfg(inp["contract"], env)
        # add ssg
        ssg_graph = interpreter.graph.ssg
        report.add_ssg(inp["contract"], ssg_graph)

    report.dump_cfg()
    report.print_cfg_graph()
    report.dump_cfg_edge_list()

    report.dump_ssg()
    report.print_ssg_graph()
    report.dump_ssg_edge_list()

    return exit_code
