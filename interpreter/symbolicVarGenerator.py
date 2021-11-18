class Generator:
    def __init__(self):
        self.countstack = 0
        self.countdata = 0
        self.path = 0

        self.overflow_name_count = {}

    @staticmethod
    def gen_contract_address(pc):
        return "contractAddress_" + str(pc)

    def gen_overflow_var(self, opcode, pc, path_id):
        if (opcode, pc, path_id) not in self.overflow_name_count:
            self.overflow_name_count[(opcode, pc, path_id)] = 0
        self.overflow_name_count[(opcode, pc, path_id)] += 1
        return "overflow_" + str(opcode) + "_" + str(pc) + "_" + str(path_id) +"_" + str(self.overflow_name_count[(opcode, pc, path_id)])

    @staticmethod
    def gen_balance_of(address):
        return "init_" + str(address)

    @staticmethod
    def gen_return_data_size(call_pc):
        return "returnSize_" + str(call_pc)

    def gen_evm_data(self, start, end):
        return "evm_" + str(start) + "_" + str(end)

    def gen_ext_code_data(self, address, start, end):
        return "bytecode_" + str(address) + "_" + str(start) + "_" + str(end)

    @staticmethod
    def gen_code_size_var(address):
        return "codeSize_" + str(address)

    def gen_return_data(self, pc, start, end, path_id):
        return "return_" + str(pc) + "_" + str(start) + "_" + str(end) + "_" + str(path_id)

    @staticmethod
    def gen_data_var(start, end):
        return "inputData_" + str(start) + "_" + str(end)

    @staticmethod
    def gen_data_size():
        return "inputSize"



    @staticmethod
    def gen_storage_var(position):
        return "storage_" + str(position)

    @staticmethod
    def gen_exp_var(v0, v1):
        return "exp_(" + str(v0) + ", " + str(v1) + ")"

    @staticmethod
    def gen_sha3_var(value):
        return "sha3_("+str(value)+")"

    @staticmethod
    def gen_gas_price_var():
        return "gasPrice"

    @staticmethod
    def gen_origin_var():
        return "origin"

    @staticmethod
    def gen_blockhash(number):
        return "blockhash_"+str(number)

    @staticmethod
    def gen_coin_base():
        return "coinbase"

    @staticmethod
    def gen_difficult():
        return "difficulty"

    @staticmethod
    def gen_gas_limit():
        return "gasLimit"

    @staticmethod
    def gen_number():
        return "blockNumber"

    @staticmethod
    def gen_timestamp():
        return "timestamp"

    def gen_path_id(self):
        self.path += 1
        return str(self.path)

    def get_path_id(self):
        return str(self.path)

    def gen_mem_var(self, pc):
        return "mem_" + str(pc) + "_" + self.get_path_id()

    def gen_gas_var(self, pc):
        return "gas_" + str(pc) + "_" + self.get_path_id()

    def gen_return_status(self, pc):
        return "returnStatus_" + str(pc) + "_" + self.get_path_id()

    # for wasm
    def gen_import_global_var(self, module, name):
        return "global_"+str(module)+str(name)

    def gen_input_var(self, index):
        return "param_" + str(index)

    def gen_local_var(self, index):
        return "local_" + str(index)

    def gen_select_var(self, index):
        self.count += 1
        return "select_"+str(index)+"_"+str(self.count)

    def gen_func_call(self, addr):
        self.count += 1
        return "call_"+str(addr)+"_"+str(self.count)


