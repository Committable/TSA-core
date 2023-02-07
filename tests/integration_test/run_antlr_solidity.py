import json
import os
import time
import traceback

import analyzer
from utils import util, global_params, context, log

cfg = util.get_config('solidity_service/config.yaml')
log.mylogger = log.get_logger()


def load_diff_file(file_path):
    with open(file_path, 'r', encoding='utf8') as load_f:
        load_dict = json.load(load_f)
        if 'ADD' not in load_dict or 'SUB' not in load_dict:
            log.mylogger.error('difference file has no "SUB" or "ADD" key')
            return {'ADD': [], 'SUB': []}
        else:
            return load_dict


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


def main():
    # diff_json = load_diff_file(
    #     './tests/diff.json')
    # global_params.DIFFS = diff_json['ADD']
    total = 0
    success = 0
    fail = 0
    failed = {'files': [], 'errors': []}
    global_params.DEST_PATH = './tmp'
    for file in load_test_files(
            './tests/integration_test/test_cases/test_file.json'):
        file_output_path = util.generate_output_dir(
            str(int(time.time() * 10**6)), '')
        total += 1
        log.mylogger.info(
            '-----------------start analysis: %s------------------',
            os.path.abspath(os.path.join(file['project_dir'],
                                         file['src_file'])))
        src_file = file['src_file']
        project_dir = file['project_dir']
        project_name = util.get_project_name(project_dir)
        ctx = context.Context(time.time(), project_dir, src_file, [], '', '')
        try:
            if 'compilation' in cfg and project_name in cfg['compilation']:
                analyzer.analyze_solidity_code_from_antlr(file_output_path, src_file,
                                               project_dir, ctx,
                                               cfg['compilation'][project_name])
            else:
                analyzer.analyze_solidity_code_from_antlr(file_output_path, src_file,
                                               project_dir, ctx)
        except Exception as err:  # pylint: disable=broad-except
            traceback.print_exc()
            fail += 1
            failed['files'].append(
                os.path.abspath(
                    os.path.join(file['project_dir'], file['src_file'])))
            failed['errors'].append(str(err))
            log.mylogger.error(
                '-----------------fail analysis: %s------------------',
                str(err))
            continue
        log.mylogger.info(
            '-----------------success analysis to %s------------------',
            file_output_path)
        success += 1

    with open(os.path.join(global_params.DEST_PATH, 'result.json'),
              'w',
              encoding='utf8') as result_file:
        json.dump(failed, result_file)

    log.mylogger.info('total: %d, success: %d, fail: %d', total, success, fail)


if __name__ == '__main__':
    main()
