import networkx as nx
import logging


from runtime.evmRuntime import EvmRuntime
from interpreter.evmInterpreter import EVMInterpreter
from inputDealer.soliditySourceMap import SourceMap
from inputDealer.inputHelper import InputHelper
from reporter.print_graph import *

logger = logging.getLogger(__name__)


def analyze_solidity_code():
    exit_code = 0
    # 0. file not exist means file not created in this commit and it's a normal condition
    source_dir = global_params.SRC_DIR
    file_path = global_params.SRC_DIR + os.sep + global_params.SRC_FILE
    if not os.path.exists(source_dir) or not os.path.exists(file_path):
        ast_graph = nx.DiGraph()
        cfg = nx.DiGraph()
        ssg = nx.DiGraph()
        print_ast_nx_graph(ast_graph, file_name="ast_graph")
        print_cfg_nx_graph(cfg, file_name="cfg")
        print_ssg_nx_graph(ssg, file_name="ssg")

        with open(os.path.join(global_params.DEST_PATH, "ast_graph.json"), 'w') as outputfile:
            json.dump({"nodes": [], "edges": []}, outputfile)

        return 0

    # 1. prepare input
    helper = InputHelper(global_params.SOLIDITY,
                         source=global_params.SRC_DIR,
                         joker=global_params.SRC_FILE,
                         compilation_err=global_params.COMPILATION_ERR)
    inputs = helper.get_solidity_inputs()

    # 2. get ast graph
    ast_graph = nx.DiGraph()
    ast_json = SourceMap.ast_helper.build_ast_graph(ast_graph)

    ast_json["source"] = inputs[0]["source_map"].source.content

    with open(os.path.join(global_params.DEST_PATH, "ast_graph.json"), 'w') as outputfile:
        json.dump(ast_json, outputfile)

    print_ast_nx_graph(ast_graph, file_name="ast_graph")

    #  there may be over one contracts in the solidity file and one contract correspones to one graph each
    cfg_graphs = []
    ssg_graphs = []

    for inp in inputs:
        logger.info("contract %s:", inp['contract'])
        cfg = nx.DiGraph()
        env = EvmRuntime(platform=global_params.PLATFORM,
                         disasm_file=inp['disasm_file'],
                         source_map=inp['source_map'],
                         source_file=inp["source"]+os.sep+inp["joker"],
                         input_type=global_params.SOLIDITY,
                         evm=inp['evm'])

        env.build_cfg()
        # env.print_cfg()
        interpreter = EVMInterpreter(env)
        return_code = interpreter.sym_exec()
        logger.info(str(interpreter.total_no_of_paths))
        if return_code != 1:
            # construct cfg
            for key in env.vertices:
                basicblock = env.vertices[key]
                label = str(basicblock.start) + "_" + str(basicblock.end)

                cfg.add_node(key, instructions=basicblock.instructions, label=label, type=basicblock.get_block_type())
            for key in env.edges:
                for target in env.edges[key]:
                    cfg.add_edge(key, target, type=env.jump_type[target])

        graph = interpreter.graph

        print_cfg_nx_graph(cfg, file_name="cfg")
        print_ssg_nx_graph(graph.ssg, file_name="ssg")

    return exit_code
