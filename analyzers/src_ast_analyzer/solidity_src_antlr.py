from analyzers.analyzer_interface import AnalyzerInterface
from ast_parsers.solidity_parser.antlr_ast_parser import AntlrAstParser
from ast_parsers.solidity_parser.antlr_ast_walker import AntlrAstWalker
from reporter.ast_reporter import AstReporter
from utils.context import Context
from typing import Dict
from analyzers.src_ast_analyzer.analyzer_base import SrcAstAnalyzerBase


class SolidityAnalyzer(AnalyzerInterface):
    def analyze(self,
                output_path: str,
                src_path: str,
                project_path: str,
                context: Context,
                compilation_cfg: Dict) -> AstReporter:
        parser = AntlrAstParser()
        walker = AntlrAstWalker()
        base_analyzer = SrcAstAnalyzerBase(parser, walker)
        return base_analyzer.analyze_primitive_ast(output_path, src_path, project_path, context)
