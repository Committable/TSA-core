from analyzers.analyzer_interface import AnalyzerInterface
from ast_parsers.move_parser.parser import MoveAstParser
from ast_parsers.move_parser.walker import MoveAstWalker
from reporter.ast_reporter import AstReporter
from utils.context import Context
from typing import Dict
from analyzers.src_ast_analyzer.analyzer_base import SrcAstAnalyzerBase


class MoveAnalyzer(AnalyzerInterface):
    def analyze(self,
                output_path: str,
                src_path: str,
                project_path: str,
                context: Context,
                compilation_cfg: Dict) -> AstReporter:
        parser = MoveAstParser()
        walker = MoveAstWalker()
        base_analyzer = SrcAstAnalyzerBase(parser, walker)
        return base_analyzer.analyze_json_ast(output_path, src_path, project_path, context)
