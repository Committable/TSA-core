import os

from z3 import *

from utils import to_unsigned

from uinttest.global_test_params import *


class EvmUnitTest(object):
    def __init__(self, name, data):
        self.name = name
        self.data = data

    def bytecode(self):
        return self.data['exec']['code'][2:]

    def storage(self):
        storage = list(self.data['post'].values())[0]['storage']
        return storage if storage != None else {"0": "0"}

    def run_test(self):
        return self._execute_vm(self.bytecode())

    def compare_with_symExec_result(self, global_state, UNIT_TEST):
        if UNIT_TEST == 2: return self.compare_real_value(global_state)
        if UNIT_TEST == 3: return self.compare_symbolic(global_state)

    def compare_real_value(self, global_state):
        storage_status = self._compare_storage_value(global_state)
        if storage_status != PASS: return storage_status
        return PASS

    def compare_symbolic(self, global_state):
        for key, value in self.storage().items():
            # key, value = long(key, 0), long(value, 0)
            try:
                symExec_result = global_state['Ia'][str(key)]
            except:
                return EMPTY_RESULT

            s = Solver()
            s.add(symExec_result == BitVecVal(value, 256))
            if s.check() == unsat: # Unsatisfy
                return FAIL
        return PASS

    def is_exception_case(self): # no post, gas field in data
        try:
            post = self.data['post']
            gas = self.data['gas']
            return False
        except:
            return True

    def _execute_vm(self, bytecode):
        self._create_bytecode_file(bytecode)
        cmd = os.system('python3 ../seraph.py -s bytecode -e -p ethereum')
        exit_code = os.WEXITSTATUS(cmd)
        return exit_code

    def _create_bytecode_file(self, bytecode):
        with open('bytecode', 'w') as code_file:
            code_file.write(bytecode)
            code_file.write('\n')
            code_file.close()

    def _compare_storage_value(self, global_state):
        for key, value in self.storage().items():
            # key, value = long(key, 0), long(value, 0)

            try:
                storage = to_unsigned(global_state['Ia'][key])
            except:
                return EMPTY_RESULT

            if storage != value:
                return FAIL
        return PASS
