import os
import traceback

from utils import global_params, log
from utils import context as ctx
from input_dealer import input_helper
from reporter import ast_reporter
from solidity_parser import parser_new, parser_old, walker
from input_dealer import solidity_source_map


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
    flag = True
    try:
        sourceUnit = parser_new.parse(source.get_content(), loc=True)
    except Exception as err:  # pylint: disable=broad-except
        flag = False
    if not flag:
        try:
            sourceUnit = parser_old.parse(source.get_content(), loc=True)
        except Exception as err:
            # todo: should not raise Exception ?
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
