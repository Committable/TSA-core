contract WithDrawFixed{
    mapping (address => uint) private userBalances;


    mapping (address => uint) private rewardsForA;

    function withdraw(address recipient) public {
        uint amountToWithdraw = userBalances[recipient];
        rewardsForA[recipient] = 0;
        if (!(recipient.call.value(amountToWithdraw)())) { throw; }
    }
}
