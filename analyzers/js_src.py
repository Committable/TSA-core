import os
import traceback


from utils import global_params, log
from utils import source as source_dealer
from utils import context as ctx
from reporter import ast_reporter
from js_parser import parser as js_parser
from js_parser import walker as js_walker


def analyze_js_code_from_treesitter(output_path,
                                    src_path,
                                    project_path,
                                    context,
                                    compilation_cfg=None):
    # 1. parse
    file_path = os.path.abspath(os.path.join(project_path, src_path))
    source = source_dealer.Source(file_path)
    sourceUnit = None
    try:
        sourceUnit = js_parser.parse(source.get_content())
    except Exception as err:
        # todo: should not raise Exception ?
        context.set_err(ctx.ExecErrorType.COMPILATION)
        traceback.print_exc()
        log.mylogger.error('fail to compile for %s, err: %s', src_path,
                           str(err))

    log.mylogger.info('get compilation outputs for file: %s', src_path)

    # 2. get report
    ast_walker = js_walker.JsAstWalker()
    ast_report = ast_reporter.AstReporter(source.get_content(), output_path)
    ast_report.set_ast_json(ast_walker.get_ast_json(sourceUnit, context))
    ast_report.set_ast_abstract(
        ast_walker.get_ast_abstract(
            ast_report.get_ast_json(),
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
