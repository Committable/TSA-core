#!/usr/bin/env python

import argparse
import time
from sys import exit

from networkx.drawing.nx_pydot import write_dot

import disassembler.params
import global_params
import interpreter.params
import reporter.params
from checker.overflow import *
from checker.reentrancy import *
from checker.tod import *
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


def main():
    global args
    parser = argparse.ArgumentParser(prog="seraph")
    group0 = parser.add_mutually_exclusive_group(required=True)
    group0.add_argument("-evm", "--evm", help="read evm bytecode in source file.", action="store_true")
    group0.add_argument("-wasm", "--wasm", help="read wasm bytecode in source file.", action="store_true")
    group0.add_argument("-sol", "--solidity", help="read solidity in source", action="store_true")
    group0.add_argument("-cc", "--cpp", help="read cpp in source file.", action="store_true")
    group0.add_argument("-go", "--golang", help="read golang in source file", action="store_true")

    group1 = parser.add_mutually_exclusive_group(required=True)
    group1.add_argument("-p", "--platform", type=str,
                        help="indicate on which blockchain blockchainPlatform the file is being verfied")

    group2 = parser.add_mutually_exclusive_group(required=True)
    group2.add_argument("-s", "--source", type=str,
                        help="local source file name. Use -e to process evm bytecode file. Use -w to process wasm bytecode file. Use -sol to process solidity. Use -cc to process cpp. Use -go to process go file")

    parser.add_argument("-v", "--version", action="version", version="%(prog)s 1.0.0")

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
        interpreter.params.TIMEOUT = args.timeout
    if args.global_timeout:
        interpreter.params.GLOBAL_TIMEOUT = args.global_timeout
    if args.tempdir:
        global_params.TMP_DIR = os.path.join(args.tempdir, str(time.time()))
    else:
        global_params.TMP_DIR = os.path.join(global_params.TMP_DIR, str(int(time.time())))

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    if args.output:
        reporter.params.DEST_PATH = args.output

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
        if has_dependencies_installed(solc=True, evm=True):
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
            logging.debug(
                "You are using an untested version of z3. %s is the officially tested version" % tested_z3_version)
    except:
        logging.critical("Z3 is not available. Please install z3 from https://github.com/Z3Prover/z3.")
        return False
    if evm:
        if not cmd_exists("evm"):
            logging.critical("Please install evm from go-ethereum and make sure it is in the path.")
            return False
        else:
            cmd = "evm --version"
            out = run_command(cmd).strip()
            evm_version = re.findall(r"evm version (\d*.\d*.\d*)", out)[0]
            disassembler.params.EVM_VERSION = evm_version
            tested_evm_version = '1.8.27'
            if compare_versions(evm_version, tested_evm_version) > 0:
                logging.warning(
                    "You are using evm version %s. The supported version is %s" % (evm_version, tested_evm_version))
    if solc:
        if not cmd_exists("solc"):
            logging.critical("solc is missing. Please install the solidity compiler and make sure solc is in the path.")
            return False
        else:
            cmd = "solc --version"
            out = run_command(cmd).strip()
            solc_version = re.findall(r"Version: (\d*.\d*.\d*)", out)[0]
            tested_solc_version = '0.4.25'
            if compare_versions(solc_version, tested_solc_version) > 0:
                logging.warning("You are using solc version %s, The latest supported version is %s" % (
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


def analyze_solidity_code():
    global args

    exit_code = 0
    helper = InputHelper(InputHelper.SOLIDITY, source=args.source, compilation_err=args.compilation_err, root_path="",
                         remap="",
                         allow_paths="")
    inputs = helper.get_inputs()
    for inp in inputs:
        logging.info("contract %s:", inp['contract'])
        env = EvmRuntime(platform=args.platform, disasm_file=inp['disasm_file'], source_map=inp["source_map"],
                         source_file=inp["source"])

        return_code = env.build_runtime_env()
        reentrancy_node_list = []
        interpreter = EVMInterpreter(env)
        interpreter.sym_exec()

        overflowChecker = Overflow(interpreter.graph)
        overflow_node_list, underflow_node_list = overflowChecker.check()
        reentrancyChecker = Reentrancy(interpreter.graph)
        reentrancy_node_list = reentrancyChecker.check()
        todChecker = TOD(interpreter.graph)
        tod_node_list = todChecker.check()

        # unfairpayment detection
        unfairapyChecker = Unfairpay(interpreter.graph)
        unfairapy_node_list = unfairapyChecker.check()

        detect_result = Result()

        overflow_pcs = []
        for overflow_node in overflow_node_list:
            overflow_pcs.append(overflow_node.global_pc)
        overflow_info = IntegerOverflowInfo(inp["source_map"], overflow_pcs)
        detect_result.results["vulnerabilities"]["integer_overflow"] = overflow_info.get_warnings()

        underflow_pcs = []
        for underflow_node in underflow_node_list:
            underflow_pcs.append(underflow_node.global_pc)
        underflow_info = IntegerUnderflowInfo(inp["source_map"], underflow_pcs)
        detect_result.results["vulnerabilities"]["integer_underflow"] = underflow_info.get_warnings()

        reentrancy_pcs = []
        # if reentrancy_node_list == None:
        for reentrancy_node in reentrancy_node_list:
            reentrancy_pcs.append(reentrancy_node.global_pc)
        reentrancy_info = ReentrancyInfo(inp["source_map"], reentrancy_pcs)
        detect_result.results["vulnerabilities"]["reentrancy"] = reentrancy_info.get_warnings()

        tod_pcs = []
        for tod_node in tod_node_list:
            tod_pcs.append(tod_node.global_pc)
        tod_info = TodBugInfo(inp["source_map"], tod_pcs)
        detect_result.results["vulnerabilities"]["tod_bug"] = tod_info.get_warnings()

        # todo: unresolved unfairpaymentInfo
        # unfairpayment detection
        # unfairpayment_pcs = []
        # for unfairpayment_node in unfairapy_node_list:
        #     unfairpayment_pcs.append(unfairpayment_node.global_pc)
        # unfairpayment_info = UnfairpaymentInfo(inp["source_map"], unfairpayment_pcs)
        # detect_result.results["vulnerabilities"]["unfairpayment"] = unfairpayment_info.get_warnings()

        separator = '\\' if sys.platform in ('win32', 'cygwin') else '/'
        result_file = "./tmp" + separator + inp['disasm_file'].split(separator)[-1].split('.evm.disasm')[0] + '.json'
        of = open(result_file, "w+")
        of.write(json.dumps(detect_result.results, indent=1))
        print("Wrote results to %s.", result_file)

        node_labels = nx.get_node_attributes(interpreter.graph.graph, 'count')
        options = {
            'node_size': 1000,
            'width': 3,
            'with_labels': node_labels
        }
        pos = nx.nx_agraph.graphviz_layout(interpreter.graph.graph)
        nx.draw(interpreter.graph.graph, pos=pos)
        write_dot(interpreter.graph.graph, 'file.dot')
        # A = nx.nx_agraph.to_agraph(interpreter.graph.graph)
        # plt.savefig("path.png")

        # helper.rm_tmp_files()

        if return_code != 0:
            exit_code = 1

    # helper.rm_tmp_files()

    return exit_code


if __name__ == '__main__':
    main()
