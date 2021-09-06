#!/usr/bin/env python

import argparse
import time
import logging
import os
import re
import subprocess
from sys import exit

import coloredlogs

import global_params
import disassembler
from utils import run_command, compare_versions
from analyze_solidity import analyze_solidity_code
from analyze_wasm_bytecode import analyze_wasm_bytecode
from analyze_evm_bytecode import analyze_evm_bytecode


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
                                    process=dict(color='magenta'))

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
                        help="source dir of project")

    parser.add_argument("-j", "--joker", type=str,
                        help="relative path of the analized file to source dir")

    parser.add_argument("-v", "--version", action="version", version="%(prog)s 1.0.0")

    parser.add_argument("-diffs", "--differences", type=str, help="differences for this file")

    parser.add_argument("-before", "--before", help="this file is before commit", action="store_true")

    parser.add_argument("-t", "--timeout", help="timeout for Z3 in ms.", type=int)

    parser.add_argument("-glt", "--global-timeout", help="timeout for tool check execution time", action="store",
                        dest="global_timeout", type=int)

    parser.add_argument("-vb", "--verbose", help="verbose output, print everything.", action="store_true")

    parser.add_argument("-ce", dest="compilation_err", action="store_true", help="show compile error details")

    parser.add_argument("-o", "--output", help="file path for results", type=str)

    parser.add_argument("-tmp", "--tempdir", help="file path for temp files", type=str)

    parser.add_argument("-db", "--debug", help="display debug information", action="store_true")

    args = parser.parse_args()

    if args.platform:
        global_params.PLATFORM = args.platform

    if args.compilation_err:
        global_params.COMPILATION_ERR = True

    if args.timeout:
        global_params.TIMEOUT = args.timeout

    if args.global_timeout:
        global_params.GLOBAL_TIMEOUT = args.global_timeout

    time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

    if args.tempdir:
        global_params.TMP_DIR = os.path.join(args.tempdir, time_str)
    else:
        global_params.TMP_DIR = os.path.join(global_params.TMP_DIR, time_str)

    if not os.path.exists(global_params.TMP_DIR):
        os.makedirs(global_params.TMP_DIR)

    if args.verbose:
        coloredlogs.install(level='DEBUG')
    else:
        coloredlogs.install(level='INFO')

    if args.source:
        if len(args.source) > 1 and args.source[-1] == os.sep:  # change from /a/b/c/ to /a/b/c
            global_params.SRC_DIR = args.source[0:-1]
        else:
            global_params.SRC_DIR = args.source
    else:
        logger.error("project source dir not assigned")
        exit(1)

    if args.joker:
        # change from ./contract to contract
        if len(args.joker) > 2 and args.joker[0] == '.' and args.joker[1] == os.sep:
            global_params.SRC_FILE = args.joker[2:]
        elif len(args.joker) > 1 and args.joker[0] == os.sep:
            logger.error("joker should be relative dir to source")
            exit(1)
        else:
            global_params.SRC_FILE = args.joker
    else:
        logger.error("analysis file not assigned")
        exit(1)

    if args.differences:
        try:
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
        except Exception as err:
            logger.error(str(err))

    if args.output:
        global_params.DEST_PATH = args.output
        if not os.path.exists(args.output):
            os.makedirs(args.output)

    exit_code = 0

    if args.evm:
        if has_dependencies_installed(evm=True):
            exit_code = analyze_evm_bytecode()
    elif args.wasm:
        if has_dependencies_installed():
            exit_code = analyze_wasm_bytecode()
    elif args.cpp:
        logger.error("cpp file not supported yet")
        exit_code = 1
    elif args.golang:
        logger.error("golang file not supported yet")
        exit_code = 1
    elif args.solidity:
        exit_code = analyze_solidity_code()

    exit(exit_code)


def cmd_exists(cmd):
    return subprocess.call("type " + cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE) == 0


def has_dependencies_installed(evm=False, emcc=False, golang=False, solc=False):
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


if __name__ == '__main__':
    main()
