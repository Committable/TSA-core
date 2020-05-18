import re
import os
import subprocess
import shlex
import logging
from utils import run_command, run_command_with_err

class SolidityCompiler:
    def __init__(self, inputHelper):
        self.inputHelper = inputHelper

    def get_compiled_contracts(self):
        if not self.inputHelper.compiled_contracts:
            self.inputHelper.compiled_contracts = self._compile_solidity()
        return self.inputHelper.compiled_contracts

    def _compile_solidity(self):
        if not self.inputHelper.allow_paths:
            cmd = "solc --bin-runtime %s %s" % (self.inputHelper.remap, self.inputHelper.source)
        else:
            cmd = "solc --bin-runtime %s %s --allow-paths %s" % (self.inputHelper.remap, self.inputHelper.source, self.inputHelper.allow_paths)
        err = ''
        if self.inputHelper.compilation_err:
            out, err = run_command_with_err(cmd)
            err = re.sub(self.inputHelper.root_path, "", err)
        else:
            out = run_command(cmd)

        libs = re.findall(r"_+(.*?)_+", out)
        libs = set(libs)
        if libs:
            return self._link_libraries(self.inputHelper.source, libs)
        else:
            return self._extract_bin_str(out, err)

    def _link_libraries(self, filename, libs):
        option = ""
        for idx, lib in enumerate(libs):
            lib_address = "0x" + hex(idx+1)[2:].zfill(40)
            option += " --libraries %s:%s" % (lib, lib_address)
        FNULL = open(os.devnull, 'w')
        if not self.inputHelper.allow_paths:
            cmd = "solc --bin-runtime %s %s" % (self.inputHelper.remap, self.inputHelper.source)
        else:
            cmd = "solc --bin-runtime %s %s --allow-paths %s" % (self.inputHelper.remap, self.inputHelper.source, self.inputHelper.allow_paths)
        p1 = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE, stderr=FNULL)
        cmd = "solc --link%s" %option
        p2 = subprocess.Popen(shlex.split(cmd), stdin=p1.stdout, stdout=subprocess.PIPE, stderr=FNULL)
        p1.stdout.close()
        out = p2.communicate()[0].decode('utf-8', 'strict')
        return self._extract_bin_str(out)

    def _extract_bin_str(self, s, err=''):
        binary_regex = r"\n======= (.*?) =======\nBinary of the runtime part: \n(.*?)\n"
        contracts = re.findall(binary_regex, s)
        contracts = [contract for contract in contracts if contract[1]]
        if not contracts:
            if not self.inputHelper.compilation_err:
                logging.critical("Solidity compilation failed. Please use -ce flag to see the detail.")
            else:
                logging.critical(err)
                logging.critical("Solidity compilation failed.")

            exit(1)
        return contracts

    def rm_tmp_files_of_multiple_contracts(self, contracts):
        for contract, _ in contracts:
            self.inputHelper.disassembler.rm_tmp_files(contract)