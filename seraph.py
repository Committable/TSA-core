#!/usr/bin/env python

import argparse
import time
from sys import exit
import coloredlogs

import disassembler.params
import reporter.params
from checker.unfairpay import *
from disassembler import wasmConvention
from inputDealer.inputHelper import InputHelper
from interpreter.evmInterpreter import EVMInterpreter
from interpreter.wasmInterpreter import WASMInterpreter
from reporter.cfgPrinter import CFGPrinter
from reporter.result import *
from reporter.vulnerability import *
from runtime.evmRuntime import EvmRuntime
from runtime.wasmRuntime import WASMRuntime
from utils import run_command, compare_versions
import networkx as nx
from inputDealer.soliditySourceMap import SourceMap
from graphviz import Digraph
from pathlib import Path

logger = logging.getLogger(__name__)


def main():
    global args
    parser = argparse.ArgumentParser(prog="seraph")
    group0 = parser.add_mutually_exclusive_group(required=True)
    group0.add_argument("-evm", "--evm", help="read evm bytecode in source file.", action="store_true")
    group0.add_argument("-wasm", "--wasm", help="read wasm bytecode in source file.", action="store_true")
    group0.add_argument("-sol", "--solidity", help="read solidity in source", action="store_true")
    group0.add_argument("-cc", "--cpp", help="read cpp in source file.", action="store_true")
    group0.add_argument("-go", "--golang", help="read golang in source file", action="store_true")

    parser.add_argument("-p", "--platform", type=str,
                        help="indicate on which blockchain blockchainPlatform the file is being verfied")

    parser.add_argument("-s", "--source", type=str,
                        help="target program's source files dir")

    parser.add_argument("-j", "--joker", type=str,
                        help="target source file name")

    parser.add_argument("-v", "--version", action="version", version="%(prog)s 1.0.0")

    parser.add_argument("-diffs", "--differences", type=str, help="differences for this file")

    parser.add_argument("-before", "--before", help="this file is before commit", action="store_true")

    parser.add_argument("-t", "--timeout", help="timeout for Z3 in ms.", type=int)

    parser.add_argument("-glt", "--global-timeout", help="timeout for tool check execution time", action="store",
                        dest="global_timeout", type=int)

    parser.add_argument("-vb", "--verbose", help="verbose output, print everything.", action="store_true")

    parser.add_argument("-ce", dest="compilation_err", action="store_true", help="show compile error details")

    parser.add_argument('-g', '--cfg',
                        action='store_true',
                        help='generate the control flow graph (CFG)')
    parser.add_argument('-c', '--call',
                        action='store_true',
                        help='generate the call flow graph')

    graph = parser.add_argument_group('Graph options')
    graph.add_argument('--simplify', action='store_true',
                       help='generate a simplify CFG')

    graph.add_argument('--onlyfunc', type=str,
                       nargs="*",
                       default=[],
                       help='only generate the CFG for this list of function name')

    parser.add_argument("-o", "--output", help="file path for results", type=str)

    parser.add_argument("-tmp", "--tempdir", help="file path for temp files", type=str)

    parser.add_argument("-db", "--debug", help="display debug information", action="store_true")

    args = parser.parse_args()

    if args.timeout:
        global_params.TIMEOUT = args.timeout

    if args.global_timeout:
        global_params.GLOBAL_TIMEOUT = args.global_timeout

    if args.tempdir:
        global_params.TMP_DIR = os.path.join(args.tempdir, str(time.time()))
    else:
        global_params.TMP_DIR = os.path.join(global_params.TMP_DIR, str(int(time.time())))

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG,
                            format='%(asctime)s [%(levelname)s] [%(filename)s:%(lineno)d]: %(message)s',
                            datefmt = '%H:%M:%S')
        coloredlogs.install(level='DEBUG')
    else:
        logging.basicConfig(level=logging.INFO,
                            format='%(asctime)s [%(levelname)s] [%(filename)s:%(lineno)d]: %(message)s',
                            datefmt = '%H:%M:%S')
        coloredlogs.DEFAULT_LOG_FORMAT = '%(asctime)s [%(levelname)s] [%(filename)s:%(lineno)d] [%(process)d]: %(message)s'
        coloredlogs.DEFAULT_DATE_FORMAT = '%H:%M:%S'
        coloredlogs.DEFAULT_FIELD_STYLES = dict(
                                            asctime=dict(color='green'),
                                            hostname=dict(color='magenta'),
                                            levelname=dict(color='black', bold=True),
                                            name=dict(color='blue'),
                                            programname=dict(color='cyan'),
                                            username=dict(color='yellow'),
                                            filename=dict(color='cyan'),
                                            lineno=dict(color='cyan'),
                                            process=dict(color='magenta')
                                        )
        coloredlogs.install(level='INFO')

    if args.source:
        global_params.SRC_DIR = args.source
    else:
        raise Exception("--source not assigned")

    if args.joker:
        global_params.SRC_FILE = args.joker
    else:
        raise Exception("--joker not assigned")

    if args.differences:
        differences = None
        with open(args.differences, 'r') as inputfile:
            differences = inputfile.readlines()
        if args.before and differences is not None:
            for i in range(0, len(differences)):
                line = differences[i]

                n = re.match(r"(['|\"]?)@@ -(\d+),(\d+) \+(\d+),(\d+) @@(.*)", line)
                if n:
                    start_line = int(n.group(2))
                    line_num = 0
                    continue

                m = re.match(r"\s*(['|\"]?)(\+|-|\s)(.*)", line)
                if m and m.group(2) == "-":
                    global_params.DIFFS.append(start_line+line_num)
                if m and m.group(2) != "+":
                    line_num += 1
        elif differences is not None:
            for i in range(0, len(differences)):
                line = differences[i]

                n = re.match(r"(['|\"]?)@@ -(\d+),(\d+) \+(\d+),(\d+) @@(.*)", line)
                if n:
                    start_line = int(n.group(4))
                    line_num = 0
                    continue

                m = re.match(r"\s*(['|\"]?)(\+|-|\s)(.*)", line)
                if m and m.group(2) == "+":
                    global_params.DIFFS.append(start_line+line_num)
                if m and m.group(2) != "-":
                    line_num += 1

    if args.output:
        reporter.params.DEST_PATH = args.output
        if not os.path.exists(args.output):
            os.makedirs(args.output)

    exit_code = 0

    if args.evm:
        if has_dependencies_installed(evm=True):
            exit_code = analyze_evm_bytecode()
    elif args.wasm:
        if has_dependencies_installed():
            exit_code = analyze_wasm_bytecode()
    if args.cpp:
        if has_dependencies_installed(emcc=True):
            exit_code = analyze_cpp_code()
    elif args.golang:
        if has_dependencies_installed(golang=True):
            exit_code = analyze_go_code()
    elif args.solidity:
        exit_code = analyze_solidity_code()

    exit(exit_code)


def cmd_exists(cmd):
    return subprocess.call("type " + cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE) == 0


def has_dependencies_installed(evm=False, emcc=False, golang=False, solc=False):
    # TODO: add emcc\golang
    try:
        import z3
        import z3.z3util
        z3_version = z3.get_version_string()
        tested_z3_version = '4.8.5'
        if compare_versions(z3_version, tested_z3_version) > 0:
            logger.debug(
                "You are using an untested version of z3. %s is the officially tested version" % tested_z3_version)
    except:
        logger.critical("Z3 is not available. Please install z3 from https://github.com/Z3Prover/z3.")
        return False
    if evm:
        if not cmd_exists("evm"):
            logger.critical("Please install evm from go-ethereum and make sure it is in the path.")
            return False
        else:
            cmd = "evm --version"
            out = run_command(cmd).strip()
            evm_version = re.findall(r"evm version (\d*.\d*.\d*)", out)[0]
            disassembler.params.EVM_VERSION = evm_version
            tested_evm_version = '1.8.27'
            if compare_versions(evm_version, tested_evm_version) > 0:
                logger.warning(
                    "You are using evm version %s. The supported version is %s" % (evm_version, tested_evm_version))
    if solc:
        if not cmd_exists("solc"):
            logger.critical("solc is missing. Please install the solidity compiler and make sure solc is in the path.")
            return False
        else:
            cmd = "solc --version"
            out = run_command(cmd).strip()
            solc_version = re.findall(r"Version: (\d*.\d*.\d*)", out)[0]
            tested_solc_version = '0.4.25'
            if compare_versions(solc_version, tested_solc_version) > 0:
                logger.warning("You are using solc version %s, The latest supported version is %s" % (
                    solc_version, tested_solc_version))
    if emcc:
        # TODO
        pass
    if golang:
        # TODO
        pass

    return True


def analyze_evm_bytecode():
    global args

    helper = InputHelper(InputHelper.EVM_BYTECODE, source=args.source)
    inp = helper.get_inputs()[0]

    env = EvmRuntime(platform=args.platform, disasm_file=inp['disasm_file'])
    env.build_runtime_env()

    interpreter = EVMInterpreter(env)
    exit_code = interpreter.sym_exec()
    # nx.draw(interpreter.graph.graph, with_labels=True)
    # output_graph = nx.nx_agraph.to_agraph(interpreter.graph)
    # print(output_graph)
    # plt.savefig("path.png")

    # helper.rm_tmp_files()

    return exit_code


def analyze_wasm_bytecode():
    # TODO
    global args

    helper = InputHelper(InputHelper.WASM_BYTECODE, source=args.source)
    inp = helper.get_inputs()[0]

    runtime = WASMRuntime(inp["module"])
    # print cfg if needed
    cprinter = None
    if args.cfg:
        if args.onlyfunc:
            func_name = args.onlyfunc[0]
            for key in runtime.module.functions_name.keys():
                if runtime.module.functions_name[key] == func_name:
                    cprinter = CFGPrinter(runtime.store.funcs[key], func_name)
            # cprinter = CFGPrinter(runtime.store.funcs[257], func_name)
            if cprinter == None:
                for export in runtime.module.exports:
                    if export.kind == wasmConvention.extern_func and export.name == func_name:
                        cprinter = CFGPrinter(runtime.store.funcs[export.desc], func_name)

    if cprinter != None:
        cprinter.print_CFG()

    runtime.__repr__()
    engine = WASMInterpreter(runtime)
    engine.exec("_initialize")

    return


def analyze_cpp_code():
    # TODO
    pass


def analyze_go_code():
    # TODO
    pass


def print_ast_nx_graph(graph1, file_name1="default", design=None, color='grey'):
    g1 = Digraph('G', filename=file_name1)
    g1.attr(rankdir='TB')
    g1.attr(overlap='scale')
    g1.attr(splines='polyline')
    g1.attr(ratio='fill')
    # g1.attr(size="7.75,10.25")

    edgelist=[]
    node_map = {}
    i = 0
    with g1.subgraph(name=file_name1, node_attr=design) as c:
        c.attr(label=file_name1)
        c.attr(color=color)
        # c.attr(fontsize='50.0')
        c.attr(overlap='false')
        c.attr(splines='polyline')
        c.attr(ratio='fill')

        for n in graph1.nodes._nodes:
            if "ischanged" not in graph1.nodes._nodes[n]:
                print("here")
            if graph1.nodes._nodes[n]["ischanged"] == True:
                c.node(str(n), label=graph1.nodes._nodes[n]["type"], splines='true', color="red")
            node_map[str(n)] = str(i)
            i += 1

        for e in graph1.edges._adjdict:
            for x in graph1.edges._adjdict[e]:
                if graph1.edges._adjdict[e][x]["ischanged"] == True:
                    c.edge(str(e), str(x), color='red')
                # else:
                #     c.edge(str(e), str(x), color='black')
                edgelist.append(node_map[str(e)]+" "+node_map[str(x)]+"\n")
            if len(graph1.edges._adjdict[e]) == 0 and "content" in graph1.nodes._nodes[e] \
                    and graph1.nodes._nodes[e]["ischanged"] == True:
                c.node(str(e)+"text", label=graph1.nodes._nodes[e]["content"], splines='True', color="green")
                c.edge(str(e), str(e)+"text", color='black')

    with open(reporter.params.DEST_PATH+os.sep+"ast_edgelist", 'w') as edgelist_file:
        edgelist_file.write("".join(edgelist))


    g1.render(file_name1, format='png', directory=reporter.params.DEST_PATH, view=False)
    # with open(os.path.join(reporter.params.DEST_PATH, file_name1+".json"),'w') as outputfile:
    #     json.dump(graph_json, outputfile)
    return


def print_cfg_nx_graph(graph1,file_name1="default", design=None, color='grey'):
    g1 = Digraph('G', filename=file_name1)
    g1.attr(rankdir='TB')
    g1.attr(overlap='scale')
    g1.attr(splines='polyline')
    g1.attr(ratio='fill')
    #g1.attr(size="7.75,10.25")

    edgelist = []
    node_map = {}
    graph_json = {}
    graph_json["nodes"] = []
    graph_json["edges"] = []
    i = 0
    with g1.subgraph(name=file_name1, node_attr=design) as c:
        c.attr(label=file_name1)
        c.attr(color=color)
        # c.attr(fontsize='50.0')
        c.attr(overlap='false')
        c.attr(splines='polyline')
        c.attr(ratio='fill')
        #c.attr(size="7.75,10.25")

        for n in graph1.nodes._nodes:
            block_type = graph1.nodes._nodes[n]["type"]
            if block_type == "falls_to":
                c.node(str(n), label=graph1.nodes._nodes[n]["label"], splines='true', color="black")
                graph_json["nodes"].append({"id":str(n), "name":graph1.nodes._nodes[n]["label"], "type":"falls_to"})
            elif block_type == "unconditional":
                c.node(str(n), label=graph1.nodes._nodes[n]["label"], splines='true', color="blue")
                graph_json["nodes"].append({"id":str(n), "name":graph1.nodes._nodes[n]["label"], "type":"unconditional"})
            elif block_type == "conditional":
                c.node(str(n), label=graph1.nodes._nodes[n]["label"], splines='true', color="green")
                graph_json["nodes"].append({"id":str(n), "name":graph1.nodes._nodes[n]["label"], "type":"conditional"})
            elif block_type == "terminal":
                c.node(str(n), label=graph1.nodes._nodes[n]["label"], splines='true', color="red")
                graph_json["nodes"].append({"id":str(n), "name":graph1.nodes._nodes[n]["label"], "type":"terminal"})
            node_map[str(n)] = str(i)
            i += 1
        for e in graph1.edges._adjdict:
            for x in graph1.edges._adjdict[e]:
                edge_type = graph1.edges._adjdict[e][x]["type"]
                if edge_type == "falls_to":
                    c.edge(str(e), str(x), color='black')
                elif edge_type == "unconditional":
                    c.edge(str(e), str(x), color='blue')
                elif edge_type == "conditional":
                    c.edge(str(e), str(x), color='green')
                elif edge_type == "terminal":
                    c.edge(str(e), str(x), color='red')
                edgelist.append(node_map[str(e)] + " " + node_map[str(x)] + "\n")
                graph_json["edges"].append({"source":str(e), "target":str(x), "type":edge_type})

    with open(reporter.params.DEST_PATH+os.sep+"cfg_edgelist", 'w') as edgelist_file:
        edgelist_file.write("".join(edgelist))

    g1.render(file_name1, format='png', directory=reporter.params.DEST_PATH, view=False)
    with open(os.path.join(reporter.params.DEST_PATH, file_name1 + ".json"),'w') as outputfile:
        json.dump(graph_json, outputfile)
    return


def print_ssg_nx_graph(graph1, file_name1="default", design=None, color='grey'):
    g1 = Digraph('G', filename=file_name1)
    g1.attr(rankdir='LR')
    g1.attr(overlap='true')
    g1.attr(splines='polyline')
    g1.attr(ratio='fill')
    #g1.attr(rotate="90")
    #g1.attr(size="7.75,10.25")

    edgelist = []
    node_map = {}
    graph_json = {}
    graph_json["nodes"] = []
    graph_json["edges"] = []
    i = 0
    with g1.subgraph(name=file_name1, node_attr=design) as c:
        c.attr(label=file_name1)
        c.attr(color=color)
        # c.attr(fontsize='50.0')
        c.attr(overlap='true')
        c.attr(splines='polyline')
        c.attr(rankdir="LR")
        c.attr(ratio='fill')
        # c.attr(rotate="90")
        # c.attr(size="7.75,10.25")

        for n in graph1.nodes._nodes:
            c.node(str(n), label=str(n).split("_")[0], splines='true', color="black")
            node_map[str(n)] = str(i)
            graph_json["nodes"].append({"id": str(n), "name": str(n).split("_")[0]})
            i += 1
        for e in graph1.edges._adjdict:
            for x in graph1.edges._adjdict[e]:
                if graph1.edges._adjdict[e][x]["label"] == "flowEdge_address":
                    c.edge(str(e), str(x), color='green')
                elif graph1.edges._adjdict[e][x]["label"] == "flowEdge_value":
                    c.edge(str(e), str(x), color='blue')
                elif graph1.edges._adjdict[e][x]["label"] == "flowEdge":
                    c.edge(str(e), str(x), color='black')
                elif graph1.edges._adjdict[e][x]["label"] == "constraint":
                    c.edge(str(e), str(x), color='red')

                edgelist.append(node_map[str(e)] + " " + node_map[str(x)] + "\n")
                graph_json["edges"].append({"source":str(e), "target":str(x), "type":graph1.edges._adjdict[e][x]["label"]})

    with open(reporter.params.DEST_PATH+os.sep+"ssg_edgelist", 'w') as edgelist_file:
        edgelist_file.write("".join(edgelist))
    g1.render(file_name1, format='png', directory=reporter.params.DEST_PATH, view=False)
    with open(os.path.join(reporter.params.DEST_PATH, file_name1 + ".json"),'w') as outputfile:
        json.dump(graph_json, outputfile)
    return


def analyze_solidity_code():
    global args
    exit_code = 0
    # 0. file not exist means file not created in this commit and it's a normal condition
    source_dir = Path(args.source)
    file_path = Path(args.source + os.sep + args.joker)
    if not source_dir.exists() or not file_path.exists():
        ast_graph = nx.DiGraph()
        cfg = nx.DiGraph()
        ssg = nx.DiGraph()
        print_ast_nx_graph(ast_graph, file_name1="ast_graph")
        print_cfg_nx_graph(cfg, file_name1="cfg")
        print_ssg_nx_graph(ssg, file_name1="ssg")

        ast_json = {}
        ast_json["nodes"] = []
        ast_json["edges"] = []
        with open(os.path.join(reporter.params.DEST_PATH, "ast_graph.json"), 'w') as outputfile:
            json.dump(ast_json, outputfile)

        return 0

    # 1. prepare input
    helper = InputHelper(global_params.SOLIDITY, source=args.source, joker=args.joker, compilation_err=args.compilation_err)
    inputs = helper.get_json_inputs()

    # 2. get ast graph
    ast_graph = nx.DiGraph()
    ast_json = SourceMap.ast_helper.build_ast_graph(ast_graph)

    with open(os.path.join(reporter.params.DEST_PATH, "ast_graph.json"), 'w') as outputfile:
        json.dump(ast_json, outputfile)

    print_ast_nx_graph(ast_graph, file_name1="ast_graph")

    cfg = nx.DiGraph()

    last = 0
    for inp in inputs:
        if len(inp["evm"]) < last:
            continue
        last = len(inp["evm"])
        logger.info("contract %s:", inp['contract'])
        env = EvmRuntime(platform=args.platform, disasm_file=inp['disasm_file'], source_map=None,
                         source_file=inp["source"], input_type="solidity-json", evm=inp['evm'])

        return_code = env.build_runtime_env()

        interpreter = EVMInterpreter(env)
        return_code = return_code or interpreter.sym_exec()
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

        print_cfg_nx_graph(cfg, file_name1="cfg")
        print_ssg_nx_graph(graph.ssg, file_name1="ssg")

    return exit_code


if __name__ == '__main__':
    main()
