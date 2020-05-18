contract IntegerOverflowMul {
    uint public count = 2;

    function run(uint256 input) public {
        count *= input;
    }
}