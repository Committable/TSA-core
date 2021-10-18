import logging
import os
import re
import subprocess
import json
import solcx

import global_params

logger = logging.getLogger(__name__)


class SolidityCompiler:
    def __init__(self, source, joker, root_path, allow_paths, remap, compilation_err):
        self.combined_json = {"contracts": {}, "sources": {}}  # compile result of json type

        self.source = source  # source dir of project
        self.joker = joker  # relative dir of the analyse file

        self.root_path = root_path
        self.allow_paths = allow_paths
        self.remap = remap
        self.compilation_err = compilation_err

        self.type = None

    def get_compiled_contracts_as_json(self):
        # 1. try with solcx
        try:
            # raise Exception
            self._compile_with_solcx()
            self.type = "solcx"
            return
        except Exception as err:
            logger.info(str(err))
        # 2. try with built-in c
        try:
            self._detect_built_in_compilation_type()
            # raise Exception
            self._compile_with_built_in_compilation()
            self._format_result()
            return
        except Exception as err:
            logger.info(str(err))

        # 3. try with detected compiler
        try:
            if self.type == "waffle":
                self._compile_with_waffle()
            elif self.type == "hardhat":
                self._deal_with_hardhat()
            elif self.type == "truffle":
                self._deal_with_truffle()
            elif self.type == "buidler":
                self._deal_with_buidler()
            return
        except Exception as err:
            logger.error(str(err))

        raise Exception("cannot compile target file: %s", self.source+os.sep+self.joker)

    def _compile_with_solcx(self):
        with open(self.source + os.sep + self.joker, 'r') as inputfile:
            version = ""
            line = inputfile.readline()
            while line:
                match_obj = re.match(r'pragma solidity ([=|>|<|\^]*)(\d*\.\d*\.\d*)(;)', line)
                if match_obj:
                    version = match_obj.group(2)
                    break
                line = inputfile.readline()
        if version != "":
            logger.info("get solc version: %s", version)
            solcx.install_solc(version)
            data_dict = solcx.compile_files([self.source + os.sep + self.joker],
                                            output_values=["abi", "bin", "bin-runtime", "ast",
                                                           "asm", "opcodes", "hashes", "srcmap-runtime"],
                                            solc_version=version,
                                            allow_empty=True,
                                            allow_paths=self.source
                                            )

            # get runtime bytecode from opcodes
            for key in data_dict:
                file = key.split(":")[0].replace(global_params.SRC_DIR+os.sep, "")
                cname = key.split(":")[-1]

                match_obj = re.match(r'.*? RETURN (INVALID|STOP) (PUSH1 0x80 PUSH1 0x40 .*)',
                                     data_dict[key]["opcodes"])

                if file not in self.combined_json["contracts"]:
                    self.combined_json["contracts"][file] = {}

                self.combined_json["contracts"][file][cname] = {
                    'evm':
                        {
                            'deployedBytecode':
                                {
                                    'opcodes': "",
                                    "object": data_dict[key]["bin-runtime"],
                                    "sourceMap": data_dict[key]["srcmap-runtime"]
                                },
                            "bytecode":
                                {
                                    'opcodes': data_dict[key]["opcodes"],
                                    "object": data_dict[key]["bin"]
                                },
                            'legacyAssembly': data_dict[key]["asm"] if "asm" in data_dict[key] else "",
                            "methodIdentifiers": data_dict[key]['hashes']
                        }
                }

                if "children" in data_dict[key]["ast"]:
                    self.combined_json["sources"][file] = {
                            "legacyAST": data_dict[key]['ast']
                        }
                    global_params.AST = "legacyAST"
                else:
                    self.combined_json["sources"][file] = {
                        "ast": data_dict[key]['ast']
                    }
                    global_params.AST = "ast"
                if match_obj:
                    self.combined_json["contracts"][file][cname]['evm']['deployedBytecode']['opcodes'] = \
                        match_obj.group(2)
                else:
                    self.combined_json["contracts"][file][cname]['evm']['deployedBytecode']['opcodes'] = \
                        data_dict[key]["opcodes"]
        if self.joker not in self.combined_json["contracts"] or self.joker not in self.combined_json["sources"]:
            raise Exception
        return

    def _compile_with_waffle(self):
        with open(os.path.join(self.source, ".waffle_bak.json"), 'w') as outputfile:
            bak_config = {
                  "compilerVersion": "./node_modules/solc",
                  "outputType": "all",
                  "compilerOptions":
                      {
                        "outputSelection":
                            {
                              "*": {
                                "*": [
                                  "evm.bytecode.object",
                                  "evm.deployedBytecode.object",
                                  "abi",
                                  "evm.legacyAssembly",
                                  "evm.bytecode.sourceMap",
                                  "evm.deployedBytecode.sourceMap",
                                  "evm.methodIdentifiers"
                                ],
                                "": ["legacyAST"]
                              }
                        },
                      }
                  }
            json.dump(bak_config, outputfile)
        child = subprocess.Popen('npx waffle .waffle_bak.json', cwd=self.source, shell=True, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
        try:
            outs, errs = child.communicate(timeout=30)
        except subprocess.TimeoutExpired:
            child.kill()
            outs, errs = child.communicate()
        if child.returncode != 0:
            logger.error(errs)
            logger.error("npx waffle compile fail")
            raise Exception
        # 2. load Combined-Json.json
        with open(self.source + os.sep + 'build' + os.sep + 'Combined-Json.json', 'r') as json_file:
            result_json = json.load(json_file)
        for key in result_json["contracts"]:
            file = key.split(":")[0]
            cname = key.split(":")[1]
            if file not in self.combined_json["contracts"]:
                self.combined_json["contracts"][file] = {}
            self.combined_json["contracts"][file][cname] = result_json["contracts"][key]
            if file not in self.combined_json["sources"]:
                self.combined_json["sources"][file] = {"legacyAST": result_json["sources"][file]["legacyAST"]}
        global_params.AST = "legacyAST"
        return

    def _compile_with_hardhat(self):
        child = subprocess.Popen('npx hardhat compile', cwd=self.source, shell=True,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
        try:
            outs, errs = child.communicate(timeout=30)
        except subprocess.TimeoutExpired:
            child.kill()
            outs, errs = child.communicate()
        if child.returncode != 0:
            logger.critical(errs)
            logger.critical("harhat compile fail")
            raise Exception
        filePath = self.source + os.sep + 'artifacts' + os.sep + "build-info"
        for i, j, files in os.walk(filePath):
            for file in files:
                with open(filePath + os.sep + file, 'r') as jsonfile:
                    single_json = json.load(jsonfile)
                    if self.joker in single_json['output']["contracts"] or self.joker in single_json['output']["sources"]:
                        self.combined_json["contracts"] = single_json['output']["contracts"]
                        self.combined_json["sources"] = single_json['output']["sources"]
                        global_params.AST = "ast"
                        return

    def _compile_with_truffle(self):
        child = subprocess.Popen('npx truffle compile', cwd=self.source, shell=True,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
        try:
            outs, errs = child.communicate(timeout=30)
        except subprocess.TimeoutExpired:
            child.kill()
            outs, errs = child.communicate()
        if child.returncode != 0:
            logger.critical(errs)
            logger.critical("harhat compile fail")
            raise Exception

    def _compile_with_buidler(self):
        child = subprocess.Popen('npx buidler compile', cwd=self.source, shell=True,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
        try:
            outs, errs = child.communicate(timeout=30)
        except subprocess.TimeoutExpired:
            child.kill()
            outs, errs = child.communicate()
        if child.returncode != 0:
            logger.critical(errs)
            logger.critical("harhat compile fail")
            raise Exception

    def _compile_with_built_in_compilation(self):
        child = subprocess.Popen('yarn compile', cwd=self.source, shell=True,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
        try:
            outs, errs = child.communicate(timeout=15)
        except subprocess.TimeoutExpired:
            child.kill()
            outs, errs = child.communicate()
        if child.returncode != 0:
            logger.critical(errs)
            logger.critical("yarn compile fail")
            raise Exception
        filePath = self.source + os.sep + 'artifacts' + os.sep + "build-info"
        for i, j, files in os.walk(filePath):
            for file in files:
                with open(filePath + os.sep + file, 'r') as jsonfile:
                    single_json = json.load(jsonfile)
                    if self.joker in single_json['output']["contracts"] or self.joker in single_json['output']["sources"]:
                        self.combined_json["contracts"] = single_json['output']["contracts"]
                        self.combined_json["sources"] = single_json['output']["sources"]
                        global_params.AST = "ast"
                        return
        # self.combined_json["contracts"] = combined_json['output']["contracts"]
        # self.combined_json["sources"] = combined_json['output']["sources"]
        logger.error("not %s in result", self.joker)

    def _detect_built_in_compilation_type(self):
        try:
            if os.path.exists(os.path.join(self.source,
                                           "hardhat.config.js")):
                self.type = "hardhad"
            elif os.path.exists(os.path.join(self.source,
                                             ".waffle.json")):
                self.type = "waffle"
            elif os.path.exists(os.path.join(self.source,
                                             "buidler.config.js")):
                self.type = "builder"
            elif os.path.exists(os.path.join(self.source,
                                             "truffle-config.js")):
                self.type = "truffle"
            else:
                self.type = "unknown"
        except Exception as err:
            self.type = "unknown"

    def _format_result(self):
        if self.type == "waffle":
            self._deal_with_waffle()
        elif self.type == "hardhat":
            self._deal_with_hardhat()
        elif self.type == "truffle":
            self._deal_with_truffle()
        elif self.type == "buidler":
            self._deal_with_buidler()
        elif self.type == "unknown":
            self._deal_with_unknown()

    def _deal_with_waffle(self):
        with open(self.source + os.sep + 'build' + os.sep + 'Combined-Json.json', 'r') as json_file:
            result_json = json.load(json_file)
        for key in result_json["contracts"]:
            file = key.split(":")[0]
            cname = key.split(":")[1]
            if file not in self.combined_json["contracts"]:
                self.combined_json["contracts"][file] = {}
            self.combined_json["contracts"][file][cname] = result_json["contracts"][key]
            if file not in self.combined_json["sources"]:
                self.combined_json["sources"][file] = {"ast": result_json["sources"][file]["AST"]}
        global_params.AST = "ast"
        return

    def _deal_with_hardhat(self):
        file_path = self.source + os.sep + 'artifacts' + os.sep + "build-info"
        for i, j, files in os.walk(file_path):
            for file in files:
                with open(file_path + os.sep + file, 'r') as jsonfile:
                    single_json = json.load(jsonfile)
                    self.combined_json["contracts"] = single_json['output']["contracts"]
                    self.combined_json["sources"] = single_json['output']["sources"]
                    global_params.AST = "ast"

    def _deal_with_truffle(self):
        return

    def _deal_with_buidler(self):
        return

    def _deal_with_unknown(self):
        return
