import logging
import os
import re

from utils import run_command_with_err


class SolidityCompiler:
    def __init__(self, source, root_path, allow_paths, remap, compilation_err, tmp_path):
        self.compiled_contracts = []
        self.source = source
        self.root_path = root_path
        self.allow_paths = allow_paths
        self.remap = remap
        self.compilation_err = compilation_err
        self.path = tmp_path
        if not os.path.exists(self.path):
            os.mkdir(self.path)


    def get_compiled_contracts(self):
        if not self.compiled_contracts:
            self.compiled_contracts = self._compile_solidity()
        return self.compiled_contracts

    def _compile_solidity(self):
        if not self.allow_paths:
            cmd = "solc --bin-runtime %s %s -o %s" % (self.remap, self.source, self.path)
        else:
            cmd = "solc --bin-runtime %s %s --allow-paths %s -o %s" % (
                self.remap, self.source, self.allow_paths, self.path)

        out, err = run_command_with_err(cmd)
        err = re.sub(self.root_path, "", err)

        return self._extract_bin_str(err)

    def _extract_bin_str(self, err):
        contracts = {}
        for root, dirs, files in os.walk(self.path):
            for file_name in files:
                if file_name.endswith(".bin-runtime"):
                    with open(os.path.join(root, file_name)) as f:
                        bytecodes = f.read()
                    contracts[os.path.join(root, file_name)] = bytecodes

            if len(contracts) == 0:
                if not self.compilation_err:
                    logging.critical("Solidity compilation failed. Please use -ce flag to see the detail.")
                else:
                    logging.critical(err)
                    logging.critical("Solidity compilation failed.")
                exit(1)

        return contracts

