#!/usr/bin/env python

import re
from sys import exit
import logging
import argparse
import subprocess
import interpreter.params
import reporter.params
import disassembler.params
from disassembler import wasmConvention
from interpreter.evmInterpreter import EVMInterpreter
# from interpreter.wasmInterpreter import WASMInterpreter
from reporter.cfgPrinter import CFGPrinter
from runtime.evmRuntime import EvmRuntime
from runtime.wasmRuntime import WASMRuntime, WasmFunc, HostFunc

from utils import run_command,compare_versions
from inputDealer.inputHelper import InputHelper

def main():
    global args
    parser = argparse.ArgumentParser(prog="seraph")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-e", "--evm", help="read evm bytecode in source file.", action="store_true")
    group.add_argument("-w", "--wasm", help="read wasm bytecode in source file.",action="store_true")
    group.add_argument("-sol", "--solidity", help="read solidity in source", action="store_true")
    group.add_argument("-cc", "--cpp", help="read cpp in source file.", action="store_true")
    group.add_argument("-go", "--golang", help="read golang in source file", action="store_true")

    group1 = parser.add_mutually_exclusive_group(required=True)
    group1.add_argument("-p", "--platform", type=str, help="indicate on which blockchain blockchainPlatform the file is being verfied")

    group2 = parser.add_mutually_exclusive_group(required=True)
    group2.add_argument("-s", "--source", type=str, help="local source file name. Use -e to process evm bytecode file. Use -w to process wasm bytecode file. Use -sol to process solidity. Use -cc to process cpp. Use -go to process go file")

    parser.add_argument("-v", "--version", action="version", version="%(prog)s 1.0.0")

    parser.add_argument("-t", "--timeout", help="Timeout for Z3 in ms.", action="store", type=int)
    parser.add_argument("-glt", "--global-timeout", help="Timeout for symbolic execution", action="store", dest="global_timeout", type=int)

    parser.add_argument("-vb", "--verbose", help="Verbose output, print everything.", action="store_true")

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
    # graph.add_argument('--visualize',

    parser.add_argument("-destpath", "--destpath", help="File path for results", action="store", dest="destpath",type=str)
    args = parser.parse_args()

    if args.timeout:
        interpreter.params.TIMEOUT = args.timeout
    if args.global_timeout:
        interpreter.params.GLOBAL_TIMEOUT = args.global_timeout

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    if args.destpath:
        reporter.params.DEST_PATH = args.destpath

    exit_code = 0
    if args.evm:
        if has_dependencies_installed(evm=True):
            exit_code = analyze_evm_bytecode()
    elif args.wasm:
        if has_dependencies_installed():
            exit_code = analyze_wasm_bytecode()
    elif args.cpp:
        if has_dependencies_installed(emcc=True):
            exit_code = analyze_cpp_code()
    elif args.golang:
        if has_dependencies_installed(golang=True):
            exit_code = analyze_go_code()
    else:
        if has_dependencies_installed(solc=True):
            exit_code = analyze_solidity_code()


    exit(exit_code)



def cmd_exists(cmd):
    return subprocess.call("type " + cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE) == 0

def has_dependencies_installed(evm=False, emcc=False, golang=False, solc=False):
    #TODO: add emcc\golang
    try:
        import z3
        import z3.z3util
        z3_version =  z3.get_version_string()
        tested_z3_version = '4.8.5'
        if compare_versions(z3_version, tested_z3_version) > 0:
            logging.debug("You are using an untested version of z3. %s is the officially tested version" % tested_z3_version)
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
            evm_version= re.findall(r"evm version (\d*.\d*.\d*)", out)[0]
            disassembler.params.EVM_VERSION = evm_version
            tested_evm_version = '1.8.27'
            if compare_versions(evm_version, tested_evm_version) > 0:
                logging.warning("You are using evm version %s. The supported version is %s" % (evm_version, tested_evm_version))
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
        #TODO
        pass
    if golang:
        #TODO
        pass

    return True

def analyze_evm_bytecode():
    global args

    helper = InputHelper(InputHelper.EVM_BYTECODE, source=args.source)
    inp = helper.get_inputs()[0]

    env = EvmRuntime(platform=args.platform, disasm_file=inp['disasm_file'])
    exit_code = env.build_runtime_env()

    interpreter=EVMInterpreter(env)
    interpreter.sym_exec()



    helper.rm_tmp_files()

    return exit_code


def analyze_wasm_bytecode():
    #TODO
    global args

    helper = InputHelper(InputHelper.WASM_BYTECODE, source=args.source)
    inp = helper.get_inputs()[0]

    runtime = WASMRuntime(inp["module"])
    #print cfg if needed
    cprinter = None
    if args.cfg:
        if args.onlyfunc:
            func_name = args.onlyfunc[0]
            for key in runtime.module.functions_name.keys():
                if runtime.module.functions_name[key] == func_name:
                    cprinter = CFGPrinter(runtime.store.funcs[key], func_name)
            if cprinter == None:
                for export in runtime.module.exports:
                    if export.kind == wasmConvention.extern_func and export.name == func_name:
                        cprinter = CFGPrinter(runtime.store.funcs[export.desc], func_name)

    if cprinter != None:
        cprinter.print_CFG()

    runtime.__repr__()
    # engine = WASMInterpreter(runtime)
    # engine.exec("_initialize")









    return

def analyze_cpp_code():
    #TODO
    pass

def analyze_go_code():
    #TODO
    pass

def analyze_solidity_code():
    #TODO
    pass

if __name__ == '__main__':
    main()