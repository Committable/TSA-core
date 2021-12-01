import logging
import os
import re
import subprocess

logger = logging.getLogger(__name__)


class EvmDisassembler:
    def __init__(self, source, contract, path):
        self.source = source
        self.contract = contract
        if not os.path.exists(path):
            os.makedirs(path)
        self.tmp = {
            "evm": os.path.join(path, contract.split(os.path.sep)[-1] + self.source.split("/")[-1].split(".")[0] + ".evm"),
            "disasm": os.path.join(path, contract.split(os.path.sep)[-1] + self.source.split("/")[-1].split(".")[0] + ".disasm")
        }

    def prepare_disasm_file(self):
        with open(self.contract, 'r') as f:
            bytecode = f.read()
        self._write_evm_file(bytecode)
        self._write_disasm_file()

    def _write_evm_file(self, bytecode):
        evm_file = self.tmp["evm"]
        with open(evm_file, 'w') as of:
            of.write(self._removeSwarmHash(bytecode))

    def get_temporary_files(self):
        return self.tmp

    def _removeSwarmHash(self, evm):
        evm_without_hash = re.sub(r"a165627a7a72305820\S{64}0029$", "", evm)
        return evm_without_hash

    def _write_disasm_file(self):
        evm_file = self.tmp["evm"]
        disasm_file = self.tmp["disasm"]
        disasm_out = ""
        try:
            disasm_p = subprocess.Popen(["evm", "disasm", evm_file], stdout=subprocess.PIPE)
            disasm_out = disasm_p.communicate()[0].decode('utf-8', 'strict')
        except:
            logger.critical("Disassembly failed.")

        with open(disasm_file, 'w') as of:
            of.write(disasm_out)
