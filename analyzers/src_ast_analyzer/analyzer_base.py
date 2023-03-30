import os
import traceback

from utils import global_params, log
from utils import source as source_dealer
from utils import context as ctx
from reporter import ast_reporter
from abstracts.ast.ast_abstract import get_ast_abstract
from ast_parsers.ast_walker_interface import AstWalkerInterface
from ast_parsers.ast_parser_interface import AstParserInterface


class SrcAstAnalyzerBase:
    def __init__(self, parser: AstParserInterface, walker: AstWalkerInterface):
        self.parser = parser
        self.walker = walker

    def analyze_json_ast(self,
                         output_path,
                         src_path,
                         project_path,
                         context):
        # 1. parse
        file_path = os.path.abspath(os.path.join(project_path, src_path))
        source = source_dealer.Source(file_path)
        source_unit = None
        try:
            source_unit = self.parser.parse(source.get_content())
        except Exception as err:
            # todo: should not raise Exception ?
            context.set_err(ctx.ExecErrorType.COMPILATION)
            traceback.print_exc()
            log.mylogger.error('fail to compile for %s, err: %s', src_path,
                               str(err))

        log.mylogger.info('get compilation outputs for file: %s', src_path)

        # 2. get report
        ast_walker = self.walker
        ast_report = ast_reporter.AstReporter(source.get_content(), output_path)
        ast_report.set_ast_json(ast_walker.get_ast_json(source_unit, context))
        ast_report.set_ast_abstract(get_ast_abstract(ast_report.get_ast_json(), ast_walker.get_type(), source, context))
        log.mylogger.info('success get ast report: %s', src_path)
        ast_report.dump_ast_json()
        ast_report.dump_ast_edge_list()
        if global_params.DEBUG_MOD:
            ast_report.print_ast_graph()
        ast_report.dump_ast_abstract()
        log.mylogger.info('success dump ast report: %s, to %s', src_path,
                          output_path)

        return ast_report

    def analyze_primitive_ast(self,
                              output_path,
                              src_path,
                              project_path,
                              context):
        # 1. parse
        file_path = os.path.abspath(os.path.join(project_path, src_path))
        source = source_dealer.Source(file_path)
        source_unit = None
        try:
            source_unit = self.parser.parse(source.get_content())
        except Exception as err:
            # todo: should not raise Exception ?
            context.set_err(ctx.ExecErrorType.COMPILATION)
            traceback.print_exc()
            log.mylogger.error('fail to compile for %s, err: %s', src_path,
                               str(err))

        log.mylogger.info('get compilation outputs for file: %s', src_path)

        # 2. get report
        ast_walker = self.walker
        ast_report = ast_reporter.AstReporter(source.get_content(), output_path)
        ast_report.set_ast_json(ast_walker.get_ast_json(source_unit, context))
        ast_report.set_ast_abstract(get_ast_abstract(source_unit, ast_walker.get_type(), source, context))
        log.mylogger.info('success get ast report: %s', src_path)
        ast_report.dump_ast_json()
        ast_report.dump_ast_edge_list()
        if global_params.DEBUG_MOD:
            ast_report.print_ast_graph()
        ast_report.dump_ast_abstract()
        log.mylogger.info('success dump ast report: %s, to %s', src_path,
                          output_path)

        return ast_report

