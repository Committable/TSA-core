import os
import time
import traceback

import memory_profiler as mem

from utils import global_params, log
from utils import context as ctx
from input_dealer import input_helper
from interpreter import evm_interpreter
from reporter import ast_reporter
from reporter import cfg_reporter
from reporter import ssg_reporter
from runtime import evm_runtime
from solidity_parser import parser, walker
from input_dealer import solidity_source_map


def analyze_evm_from_solidity(output_path,
                              src_path,
                              project_path,
                              context,
                              compilation_cfg=None):
    # 0. make output dirs
    if not os.path.exists(output_path):
        os.makedirs(output_path)
    # 1. prepare input
    if compilation_cfg is None:
        compilation_cfg = {}
    helper = input_helper.InputHelper(
        global_params.LanguageType.SOLIDITY,
        project_dir=project_path,
        src_file=src_path,
        root_path=context.root_path,
        remaps=context.remaps,
        allow_paths=context.
        allow_paths,  # TODO(Yang): allow paths is overlapped by include paths?
        include_paths=context.include_paths,
        compiler_version='',
        compilation_err=global_params.COMPILATION_ERR)
    # 2. compile
    flag = True  # represent the compilation error caused by source file
    try:
        inputs, flag = helper.get_solidity_inputs(compilation_cfg, output_path)
    except Exception as err:  # pylint: disable=broad-except
        context.set_err(ctx.ExecErrorType.COMPILATION)
        traceback.print_exc()
        log.mylogger.error('fail to compile for %s, err: %s', src_path,
                           str(err))
        inputs = []
    # compilation fail without an exception
    if not flag:
        context.set_err(ctx.ExecErrorType.COMPILATION)
        log.mylogger.error('fail to compile for %s', src_path)

    log.mylogger.info('get compilation outputs for file: %s', src_path)

    # 3. symbolic execution,
    # There may be over one contracts in the solidity file,
    # and one contract to one graph each.
    cfg_report = cfg_reporter.CfgReporter(output_path)
    ssg_report = ssg_reporter.SsgReporter(output_path)

    for inp in inputs:
        log.mylogger.info('begin analysing contract: %s:', inp['contract'])
        start_time = time.time()
        start_mem = mem.memory_usage()

        env = evm_runtime.EvmRuntime(
            context,
            platform=context.platform,
            opcodes=inp['opcodes'],
            source_map=inp['source_map'],
            src_file=inp['src_file'],
            input_type=global_params.LanguageType.SOLIDITY,
            binary=inp['binary'])

        env.build_cfg()
        interpreter = evm_interpreter.EVMInterpreter(env, inp['contract'],
                                                     context)
        interpreter.sym_exec()

        # add cfg
        cfg_report.set_contract_cfg(inp['contract'], env)
        # add ssg
        ssg_report.set_contract_ssg(inp['contract'], interpreter.x_graph)
        # add coverage information
        cfg_report.set_coverage_info(inp['contract'], env, interpreter)
        if global_params.DEBUG_MOD:
            env.print_visited_cfg(interpreter.total_visited_edges, interpreter.impossible_paths, output_path)
        end_mem = mem.memory_usage()
        end_time = time.time()
        execution_time = end_time - start_time
        used_mem = end_mem[0] - start_mem[0]
        log.mylogger.info(
            'End analysing contract %s, using time: %.6f s, mem: %.2f M',
            inp['contract'], execution_time, used_mem)
        if context.timeout:
            break

    log.mylogger.info('success get report: %s', src_path)

    cfg_report.construct_cfg_abstract(context)

    cfg_report.dump_cfg_json()
    cfg_report.dump_cfg_edge_list()
    cfg_report.dump_cfg_abstract()

    if global_params.DEBUG_MOD:
        cfg_report.print_cfg_graph()
        cfg_report.print_contract_cfg_graph()

    ssg_report.construct_ssg_abstract(context)

    ssg_report.dump_ssg_json()
    ssg_report.dump_ssg_edge_list()
    ssg_report.dump_ssg_abstract()

    if global_params.DEBUG_MOD:
        ssg_report.print_ssg_graph()
        ssg_report.print_function_ssg_graph()
    log.mylogger.info('success dump report: %s, to %s', src_path, output_path)

    return cfg_report, ssg_report


def analyze_solidity_code(output_path,
                          src_path,
                          project_path,
                          context,
                          compilation_cfg=None):
    # 1. prepare input
    if compilation_cfg is None:
        compilation_cfg = {}
    helper = input_helper.InputHelper(
        global_params.LanguageType.SOLIDITY,
        project_dir=project_path,
        src_file=src_path,
        root_path=context.root_path,
        remaps=context.remaps,
        allow_paths=context.allow_paths,
        include_paths=context.include_paths,
        compiler_version='',
        compilation_err=global_params.COMPILATION_ERR)
    # 2. compile
    flag = True
    try:
        inputs, flag = helper.get_solidity_inputs(compilation_cfg, output_path)
        del inputs  # Unused, reserve for name hint
    except Exception as err:  # pylint: disable=broad-except
        context.set_err(ctx.ExecErrorType.COMPILATION)
        traceback.print_exc()
        log.mylogger.error('fail to compile for %s, err: %s', src_path,
                           str(err))
    if not flag:
        context.set_err(ctx.ExecErrorType.COMPILATION)
        log.mylogger.error('fail to compile for %s', src_path)

    log.mylogger.info('get compilation outputs for file: %s', src_path)

    # 3. get report
    ast_report = ast_reporter.AstReporter(helper.source.get_content(),
                                          output_path)
    ast_report.set_ast_json(
        helper.ast_helper.get_ast_json(
            os.path.abspath(os.path.join(project_path, src_path)),
            helper.source, context))
    ast_report.set_ast_abstract(
        helper.ast_helper.get_ast_abstract(
            os.path.abspath(os.path.join(project_path, src_path)),
            helper.source, context))
    log.mylogger.info('success get ast report: %s', src_path)
    ast_report.dump_ast_json()
    ast_report.dump_ast_edge_list()
    if global_params.DEBUG_MOD:
        ast_report.print_ast_graph()
    ast_report.dump_ast_abstract()
    log.mylogger.info('success dump ast report: %s, to %s', src_path,
                      output_path)

    return ast_report


def analyze_solidity_code_from_antlr(output_path,
                                      src_path,
                                      project_path,
                                      context,
                                      compilation_cfg=None):
    # 1. parse
    file_path = os.path.abspath(os.path.join(project_path, src_path))
    source = solidity_source_map.Source(file_path)
    sourceUnit = None
    try:
        sourceUnit = parser.parse(source.get_content(), loc=True)
    except Exception as err:  # pylint: disable=broad-except
        context.set_err(ctx.ExecErrorType.COMPILATION)
        traceback.print_exc()
        log.mylogger.error('fail to compile for %s, err: %s', src_path,
                           str(err))

    log.mylogger.info('get compilation outputs for file: %s', src_path)

    # 2. get report
    ast_walker = walker.AntlrAstWalker()
    ast_report = ast_reporter.AstReporter(source.get_content(), output_path)
    ast_report.set_ast_json(ast_walker.get_ast_json(sourceUnit, context))
    ast_report.set_ast_abstract(
        ast_walker.get_ast_abstract(
            sourceUnit,
            source, context))
    log.mylogger.info('success get ast report: %s', src_path)
    ast_report.dump_ast_json()
    ast_report.dump_ast_edge_list()
    if global_params.DEBUG_MOD:
        ast_report.print_ast_graph()
    ast_report.dump_ast_abstract()
    log.mylogger.info('success dump ast report: %s, to %s', src_path,
                      output_path)

    return ast_report
