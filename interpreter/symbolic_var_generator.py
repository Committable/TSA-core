class Generator:
    def __init__(self):
        self.path = 0
    # todo: str() of symbolic expression is time-consuming

    @staticmethod
    def gen_contract_address(pc):
        return "contractAddress_" + str(pc)

    @staticmethod
    def gen_balance_of(address):
        return "init_" + str(address)

    @staticmethod
    def gen_return_data_size(call_pc):
        return "returnSize_" + str(call_pc)

    @staticmethod
    def gen_evm_data(start, end):
        return "evm_" + str(start) + "_" + str(end)

    @staticmethod
    def gen_ext_code_data(address, start, end):
        return "bytecode_" + str(address) + "_" + str(start) + "_" + str(end)

    @staticmethod
    def gen_code_size_var(address):
        return "codeSize_" + str(address)

    @staticmethod
    def gen_code_size_var(address):
        return "codeHash_" + str(address)

    def gen_return_data(self, pc, start, end, path_id):
        return "return_" + str(pc) + "_" + str(start) + "_" + str(end) + "_" + str(path_id)

    @staticmethod
    def gen_data_var(start, end, function):
        return "inputData_" + str(start) + "_" + str(end) + "_" + function

    @staticmethod
    def gen_data_size():
        return "inputSize"

    @staticmethod
    def gen_storage_var(position):
        return "state_" + str(position)

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
    def gen_chain_id():
        return "chainId"

    @staticmethod
    def gen_base_fee():
        return "baseFee"

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

    @staticmethod
    def gen_mem_var(pc):
        return "mem_" + str(pc)

    @staticmethod
    def gen_gas_var(pc):
        return "gas_" + str(pc)

    @staticmethod
    def gen_return_status(pc):
        return "returnStatus_" + str(pc)


