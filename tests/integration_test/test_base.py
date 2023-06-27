import json
import os
import time
import traceback

from analyzers.analyzer_interface import AnalyzerInterface
from utils import util, global_params, context, log


def load_test_files(file_path):
    result = []
    with open(file_path, 'r', encoding='utf8') as load_f:
        load_dict = json.load(load_f)
    if 'projects' in load_dict:
        for project in load_dict['projects']:
            for path, dirs, fs in os.walk(project):
                del dirs  # Unused, reserve for name hint
                for f in fs:
                    if os.path.splitext(f)[-1][1:] == 'sol':
                        file_dir = util.change_to_relative(
                            util.remove_prefix(str(path), project))
                        result.append({
                            'project_dir': project,
                            'src_file': os.path.join(file_dir, f)
                        })
    if 'files' in load_dict:
        for file in load_dict['files']:
            result.append(file)
    return result


class TestBase:
    def __init__(self, cfg, analyzer: AnalyzerInterface):
        self.cfg = cfg
        self.analyzer = analyzer
        global_params.DEST_PATH = "./tmp"

    def run_test_from_json(self, test_path):
        total = 0
        success = 0
        fail = 0
        failed = {'files': [], 'errors': []}
        for file in load_test_files(test_path):
            file_output_path = util.generate_output_dir(str(int(time.time() * 10 ** 6)), '')
            total += 1
            log.mylogger.info('-----------------start analysis: %s------------------',
                              os.path.abspath(os.path.join(file['project_dir'], file['src_file']))
                              )
            src_file = file['src_file']
            project_dir = file['project_dir']
            diff = util.get_diff("./tests/integration_test/test_cases/difference3", True)
            ctx = context.Context(time.time(), project_dir, src_file, diff, '', ast_abstracts=global_params.AST)
            try:
                self.analyzer.analyze(file_output_path, src_file, project_dir, ctx, {})
            except Exception as err:  # pylint: disable=broad-except
                traceback.print_exc()
                fail += 1
                failed['files'].append(os.path.abspath(os.path.join(file['project_dir'], file['src_file'])))
                failed['errors'].append(str(err))
                log.mylogger.error('-----------------fail analysis: %s------------------',str(err))
                continue
            log.mylogger.info('-----------------success analysis to %s------------------', file_output_path)
            success += 1

        with open(os.path.join(global_params.DEST_PATH, 'result.json'), 'w', encoding='utf8') as result_file:
            json.dump(failed, result_file)

        log.mylogger.info('total: %d, success: %d, fail: %d', total, success, fail)
