from analyzers.analyzer_interface import AnalyzerInterface
from ast_parsers.rust_parser.parser import RustAstParser
from ast_parsers.rust_parser.walker import RustAstWalker
from reporter.ast_reporter import AstReporter
from utils.context import Context
from typing import Dict
from analyzers.src_ast_analyzer.analyzer_base import SrcAstAnalyzerBase


class RustAnalyzer(AnalyzerInterface):

    def analyze(self, output_path: str, src_path: str, project_path: str,
                context: Context, compilation_cfg: Dict) -> AstReporter:
        parser = RustAstParser()
        walker = RustAstWalker()
        base_analyzer = SrcAstAnalyzerBase(parser, walker)
        return base_analyzer.analyze_json_ast(output_path, src_path,
                                              project_path, context)
