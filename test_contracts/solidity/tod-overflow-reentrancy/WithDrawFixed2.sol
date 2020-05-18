contract WithDrawLock{
    mapping (address => uint) private balances;
    bool private lockBalances;

    function deposit() payable public returns (bool) {
        if (!lockBalances) {
            lockBalances = true;
            balances[msg.sender] += msg.value;
            lockBalances = false;
            return true;
        }
        throw;
    }

    function withdraw(uint amount) payable public returns (bool) {
        if (!lockBalances && amount > 0 && balances[msg.sender] >= amount) {
            lockBalances = true;

            if (msg.sender.call.value(amount)()) { // Normally insecure, but the mutex saves it
              balances[msg.sender] -= amount;
            }

            lockBalances = false;
            return true;
        }

        throw;
    }
}