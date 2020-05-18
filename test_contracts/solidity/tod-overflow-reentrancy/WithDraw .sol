contract WithDraw{
    mapping (address => uint) private userBalances;


    mapping (address => uint) private rewardsForA;

    function withdraw(address recipient) public {
        uint amountToWithdraw = userBalances[recipient];
        if (!(recipient.call.value(amountToWithdraw)())) { throw; }
        rewardsForA[recipient] = 0;
    }
}
