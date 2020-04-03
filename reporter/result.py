import re
import logging
import log


class Result:

    def __init__(self):
        self.results = {
            'evm_code_coverage': '',
            'vulnerabilities': {
                'integer_underflow': [],
                'integer_overflow': [],
                'reentrancy': [],
                'prng_bug': [],
                'dos_bug': [],
                'tod_bug': []
            },
            'run_time': 0
        }
        self.start_time = 0

    def set_start_time(self, start_time):
        self.start_time = start_time

    def set_evm_code_coverage(self, coverage):
        self.results['evm_code_coverage'] = coverage

    def set_bug_info(self, bug_id, bug_type):
        self.results['vulnerabilities'][bug_id] = bug_type.get_warnings()

    def return_result(self):
        return self.results


def web_case_detail(bug_type, bug_id):
    global g_src_map
    global d_results

    for key in bug_type.get_pcs():
        source_code = g_src_map.get_source_code(key)
        if not source_code:
            continue

        source_code = g_src_map.get_buggy_line(key)
        new_line_idx = source_code.find('\n')
        source_code = source_code.split('\n', 1)[0]
        location = g_src_map.get_location(key)

        source = re.sub(g_src_map.root_path, '', g_src_map.get_filename())
        line = location['begin']['line'] + 1
        column = location['begin']['column'] + 1
        s = '%s:%s: Warning: ' % (line, column)
        s += source_code
        # if new_line_idx != -1:
        #     stripped_s = source_code.lstrip('[ \t]')
        #     len_of_leading_spaces = len(source_code) - len(stripped_s)
        #     s += '\n' + source_code[0:len_of_leading_spaces] + '^\n'
        #     s += 'Spanning multiple lines.'
        source_code = s

        dic = {}
        dic["bug_abstract"]=str(bug_type.get_types()[key])
        dic["bug_line"]=source_code
        dic["bug_test_case"]= str(bug_type.report_test_case(key))

        if bug_id == 1:
            log.info('Bug Abstract: ' + str(bug_type.get_types()[key]))
            log.info('Bug Line: ' + source_code)
            # path=print_dot_cfg_path(global_params.BUG_BLOCK_PATH['REENTRANCY'][key],global_params.BUG_TEST_CASE['REENTRANCY'][key])
            # dic["bug_cfg"] = str(path)
            log.info('Bug test case: ' + str(bug_type.report_test_case(key)))
            d_results["vulnerabilities"]["reentrancy"].append(dic)
        elif bug_id == 2:
            log.info('Bug Abstract: ' + str(bug_type.get_types()[key]))
            log.info('Bug Line: ' + source_code)
            # path=print_dot_cfg_path(global_params.BUG_BLOCK_PATH['PRNG'][key],global_params.BUG_TEST_CASE['PRNG'][key])
            # dic["bug_cfg"] = str(path)
            log.info('Bug test case: ' + str(bug_type.report_test_case(key)))
            d_results["vulnerabilities"]["prng_bug"].append(dic)
        elif bug_id == 3:
            log.info('Bug Abstract: ' + str(bug_type.get_types()[key]))
            log.info('Bug Line: ' + source_code)
            # path=print_dot_cfg_path(global_params.BUG_BLOCK_PATH['OVERFLOW'][key],global_params.BUG_TEST_CASE['OVERFLOW'][key])
            # dic["bug_cfg"] = str(path)
            log.info('Bug test case: ' + str(bug_type.report_test_case(key)))
            d_results["vulnerabilities"]["integer_overflow"].append(dic)
        elif bug_id == 4:
            log.info('Bug Abstract: ' + str(bug_type.get_types()[key]))
            log.info('Bug Line: ' + source_code)
            # path=print_dot_cfg_path(global_params.BUG_BLOCK_PATH['TOD'][key],global_params.BUG_TEST_CASE['TOD'][key])
            # dic["bug_cfg"] = str(path)
            log.info('Bug test case: ' + str(bug_type.report_test_case(key)))
            d_results["vulnerabilities"]["tod_bug"].append(dic)
        elif bug_id == 5:
            log.info('Bug Abstract: ' + str(bug_type.get_types()[key]))
            log.info('Bug Line: ' + source_code)
            # path=print_dot_cfg_path(global_params.BUG_BLOCK_PATH['DOS'][key],global_params.BUG_TEST_CASE['DOS'][key])
            # dic["bug_cfg"] = str(path)
            log.info('Bug test case: ' + str(bug_type.report_test_case(key)))
            d_results["vulnerabilities"]["dos_bug"].append(dic)
        elif bug_id == 6:
            log.info('Bug Abstract: ' + str(bug_type.get_types()[key]))
            log.info('Bug Line: ' + source_code)
            # path=print_dot_cfg_path(global_params.BUG_BLOCK_PATH['ASSERTFAIL'][key],global_params.BUG_TEST_CASE['ASSERTFAIL'][key])
            # dic["bug_cfg"] = str(path)
            log.info('Bug test case: ' + str(bug_type.report_test_case(key)))
        elif bug_id == 7:
            log.info('Bug Abstract: ' + str(bug_type.get_types()[key]))
            log.info('Bug Line: ' + source_code)
            # path=print_dot_cfg_path(global_params.BUG_BLOCK_PATH['UNDERFLOW'][key],global_params.BUG_TEST_CASE['UNDERFLOW'][key])
            # dic["bug_cfg"] = str(path)
            log.info('Bug test case: ' + str(bug_type.report_test_case(key)))
            d_results["vulnerabilities"]["integer_underflow"].append(dic)