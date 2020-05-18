import re
import os
import logging
import subprocess

class EvmDisassembler:
    def __init__(self, inputHelper):
        self.inputHelpr = inputHelper

    def prepare_disasm_file(self, target, bytecode):
        self._write_evm_file(target, bytecode)
        self._write_disasm_file(target)

    def _write_evm_file(self, target, bytecode):
        evm_file = self.get_temporary_files(target)["evm"]
        with open(evm_file, 'w') as of:
            of.write(self._removeSwarmHash(bytecode))

    def get_temporary_files(self, target):
        return {
            "evm": target + ".evm",
            "disasm": target + ".evm.disasm",
            "log": target + ".evm.disasm.log"
        }

    def _removeSwarmHash(self, evm):
        evm_without_hash = re.sub(r"a165627a7a72305820\S{64}0029$", "", evm)
        return evm_without_hash

    def _write_disasm_file(self, target):
        tmp_files = self.get_temporary_files(target)
        evm_file = tmp_files["evm"]
        disasm_file = tmp_files["disasm"]
        disasm_out = ""
        try:
            disasm_p = subprocess.Popen(["evm", "disasm", evm_file], stdout=subprocess.PIPE)
            disasm_out = disasm_p.communicate()[0].decode('utf-8', 'strict')
        except:
            logging.critical("Disassembly failed.")
            exit(1)

        with open(disasm_file, 'w') as of:
            of.write(disasm_out)

    def rm_tmp_files(self, target):
        tmp_files = self.get_temporary_files(target)
        if not self.inputHelpr.evm:
            self._rm_file(tmp_files["evm"])
            self._rm_file(tmp_files["disasm"])
        self._rm_file(tmp_files["log"])

    def _rm_file(self, path):
        if os.path.isfile(path):
            os.unlink(path)