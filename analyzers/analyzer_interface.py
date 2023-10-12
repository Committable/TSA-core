from abc import ABCMeta, abstractmethod
from reporter.ast_reporter import AstReporter
from utils.context import Context
from typing import Dict


class AnalyzerInterface(metaclass=ABCMeta):

    @abstractmethod
    def analyze(self, output_path: str, src_path: str, project_path: str,
                context: Context, compilation_cfg: Dict) -> AstReporter:
        pass
