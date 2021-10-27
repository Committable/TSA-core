import logging
import os
import re
import subprocess
import json
import solcx
import signal
import shutil

from pyevmasm import disassemble_hex

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

        self.parse_files = []

    def get_compiled_contracts_as_json(self):
        # 1. try with solcx
        try:
            #raise Exception
            self._compile_with_solcx()
            self.type = "solcx"
            self._convert_opcodes()
            return
        except Exception as err:
            logger.error(str(err))

        # 2. try with detected compiler
        try:
            self._detect_built_in_compilation_type()
            if self.type == "waffle":
                self._compile_with_waffle()
            elif self.type == "hardhat":
                self._compile_with_hardhat()
            elif self.type == "truffle":
                self._compile_with_truffle()
            elif self.type == "buidler":
                self._compile_with_buidler()
            else:
                raise Exception("cannot detect built-in compilation type")
            self._convert_opcodes()
            return
        except Exception as err:
            logger.error(str(err))

        # 3. try with built-in c
        try:
            self._compile_with_built_in_compilation()
            self._format_result()
            self._convert_opcodes()
            return
        except Exception as err:
            logger.error(str(err))

        # 4. compile with default truffle
        try:
            self._compile_with_default_truffle()
            self._convert_opcodes()
            return
        except Exception as err:
            logger.error(str(err))

        raise Exception("cannot compile target file: %s", self.source+os.sep+self.joker)

    def _compile_with_solcx(self):
        version = self._get_solc_version(os.path.join(self.source, self.joker))
        if version != "":
            logger.info("get solc version: %s", version)
            if self._compare_version("0.4.11", version):
                version = "0.4.11"
            solcx.install_solc(version)
            data_dict = solcx.compile_files([self.source + os.sep + self.joker],
                                            output_values=["abi", "bin", "bin-runtime", "ast",
                                                           "asm", "opcodes", "srcmap-runtime"],
                                            solc_version=version,
                                            allow_empty=True,
                                            allow_paths=self.source
                                            )

            # get runtime bytecode from opcodes
            for key in data_dict:
                file = key.split(":")[0].replace(global_params.SRC_DIR+os.sep, "")
                cname = key.split(":")[-1]

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
        if self.joker not in self.combined_json["contracts"] or self.joker not in self.combined_json["sources"]:
            raise Exception("solc::not %s in compiler result", self.joker)
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
            outs, errs = child.communicate(timeout=60)
        except subprocess.TimeoutExpired:
            child.kill()
            child.terminate()
            os.killpg(child.pid, signal.SIGTERM)
            raise Exception("npx waffle compile fail: timeout")
        if child.returncode != 0:
            raise Exception("npx waffle compile fail: %s", errs)
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
            outs, errs = child.communicate(timeout=60)
        except subprocess.TimeoutExpired:
            child.kill()
            child.terminate()
            os.killpg(child.pid, signal.SIGTERM)
            raise Exception("npx waffle compile fail: timeout")
        if child.returncode != 0:
            raise Exception("harhat compile fail: %s", errs)
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
            outs, errs = child.communicate(timeout=60)
        except subprocess.TimeoutExpired:
            child.kill()
            child.terminate()
            os.killpg(child.pid, signal.SIGTERM)
            raise Exception("npx waffle compile fail: timeout")
        if child.returncode != 0:
            raise Exception("npx truffle fail: %s", errs)
        self._deal_with_truffle()

    def _compile_with_buidler(self):
        child = subprocess.Popen('npx buidler compile', cwd=self.source, shell=True,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
        try:
            outs, errs = child.communicate(timeout=60)
        except subprocess.TimeoutExpired:
            child.kill()
            child.terminate()
            os.killpg(child.pid, signal.SIGTERM)
            raise Exception("npx waffle compile fail: timeout")
        if child.returncode != 0:
            raise Exception("harhat compile fail: %s", errs)
        self._deal_with_buidler()

    def _compile_with_built_in_compilation(self):
        child = subprocess.Popen('yarn compile', cwd=self.source, shell=True,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
        try:
            outs, errs = child.communicate(timeout=60)
        except subprocess.TimeoutExpired:
            child.kill()
            child.terminate()
            os.killpg(child.pid, signal.SIGTERM)
            raise Exception("yarn compile fail: timeout")
        if child.returncode != 0:
            logger.error(errs)
            logger.error("yarn compile fail")
            raise Exception

    def _detect_built_in_compilation_type(self):
        try:
            if os.path.exists(os.path.join(self.source,
                                           "hardhat.config.js")):
                self.type = "hardhat"
            elif os.path.exists(os.path.join(self.source,
                                             ".waffle.json")):
                self.type = "waffle"
            elif os.path.exists(os.path.join(self.source,
                                             "buidler.config.js")):
                self.type = "buidler"
            elif os.path.exists(os.path.join(self.source,
                                             "truffle-config.js")) or \
                os.path.exists(os.path.join(self.source,
                                            "truffle.js")):
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
        if not os.path.exists(os.path.join(self.source, "build/contracts", self.joker.split(os.sep)[-1].split(".")[0]+".json")):
            raise Exception("result not in build dir")
        with open(os.path.join(self.source, "build/contracts", self.joker.split(os.sep)[-1].split(".")[0]+".json")) as jsonfile:
            result = json.load(jsonfile)
            file = self.joker
            cname = result["contractName"]
            self.combined_json["contracts"][file] = {}
            self.combined_json["contracts"][file][cname] = {
                'evm':
                    {
                        'deployedBytecode':
                            {
                                'opcodes': "",
                                "object": result["deployedBytecode"] if "deployedBytecode" in result else "",
                                "sourceMap": result["deployedSourceMap"] if "deployedSourceMap" in result else ""
                            },
                        "bytecode":
                            {
                                'opcodes': "",
                                "object": result["bytecode"] if "deployedSourceMap" in result else ""
                            },
                    }
            }
            self.combined_json["sources"][file] = {
                "ast": result['ast'] if "deployedSourceMap" in result else ""
            }
            global_params.AST = "ast"
        return

    def _deal_with_buidler(self):
        if not os.path.exists(os.path.join(self.source, "cache/solc-output.json")):
            raise Exception("buidler result not exit")
        with open(os.path.join(self.source, "cache/solc-output.json"), 'r') as jsonfile:
            self.combined_json = json.load(jsonfile)
            global_params.AST = "ast"
        return

    def _deal_with_unknown(self):
        self._deal_with_truffle()

    def _compile_with_default_truffle(self):
        if os.path.exists(os.path.join(self.source, "truffle.js")):
            os.remove(os.path.join(self.source, "truffle.js"))
        if os.path.exists(os.path.join(self.source, "truffle-config.js")):
            os.remove(os.path.join(self.source, "truffle-config.js"))
        with open(os.path.join(self.source, "truffle.js"), 'w') as outputfile:
            bak_config = "module.exports = {};"
            outputfile.write(bak_config)
        self._compile_with_truffle()

    def _convert_opcodes(self):
        if "contracts" in self.combined_json and self.joker in self.combined_json["contracts"]:
            for cname in self.combined_json["contracts"][self.joker]:
                x = self.combined_json["contracts"][self.joker][cname]
                deployed_bytecode_object = x["evm"]["deployedBytecode"]['object']
                if deployed_bytecode_object:
                    x["evm"]["deployedBytecode"]['opcodes'] = disassemble_hex(deployed_bytecode_object).replace("\n", " ")

                bytecode_object = x["evm"]["bytecode"]['object']
                if bytecode_object and not x["evm"]["bytecode"]['opcodes']:
                    x["evm"]["bytecode"]['opcodes'] = disassemble_hex(bytecode_object).replace("\n", " ")

    def rm_compiled_files(self):
        if os.path.exists(os.path.join(self.source, "build")):
            shutil.rmtree(os.path.join(self.source, "build"))
        if os.path.exists(os.path.join(self.source, "artifacts")):
            shutil.rmtree(os.path.join(self.source, "artifacts"))
        if os.path.exists(os.path.join(self.source, "cache")):
            shutil.rmtree(os.path.join(self.source, "cache"))

    def _get_solc_version(self, file):
        if file in self.parse_files:
            return "0.0.0"
        self.parse_files.append(file)
        import_files = []
        with open(file, 'r') as inputfile:
            version = ""
            lines = inputfile.readlines()
            i = 0
            for line in lines:
                match_obj = re.match(r'pragma solidity ([=|>|<|\^]*)(\d*\.\d*\.\d*)(.*)\n', line)
                i += 1
                if match_obj:
                    version = match_obj.group(2)
                    break
                line = inputfile.readline()
            for line in lines[i:]:
                match_obj = re.match(r'import "(.*)";\n', line)
                if match_obj:
                    import_files.append(match_obj.group(1))
                else:
                    if line != "\n":
                        break
        current_dir = os.path.dirname(file)
        for x in import_files:
            other_version = self._get_solc_version(os.path.abspath(os.path.join(current_dir, x)))
            if not self._compare_version(version, other_version):
                version = other_version

        return version

    def _compare_version(self, version1, version2):
        parts1 = version1.split(".")
        parts2 = version2.split(".")
        length = len(parts1) if len(parts1) <= len(parts2) else len(parts2)
        for x in range(0, length):
            if int(parts1[x]) > int(parts2[x]):
                return True
            elif int(parts1[x]) < int(parts2[x]):
                return False
        return len(parts1) >= len(parts2)