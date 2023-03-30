from analyzers.src_ast_analyzer.rust_src import RustAnalyzer
from tests.integration_test.test_base import TestBase
from utils import util, log

cfg = util.get_config('services/rust_service/config.yaml')
log.mylogger = log.get_logger()


def main():
    analyzer = RustAnalyzer()
    base = TestBase(cfg, analyzer)
    base.run_test_from_json('tests/integration_test/test_cases/test_file.json')


if __name__ == '__main__':
    main()
