contract MyAdvancedToken{

    uint256 public sellPrice;
    uint256 public buyPrice;

    mapping (address => uint256) public balanceOf;

    function setPrices(uint256 newSellPrice, uint256 newBuyPrice) {
        sellPrice = newSellPrice;
        buyPrice = newBuyPrice;
    }

    function buy() payable {
        uint amount = msg.value / buyPrice;                // calculates the amount
        if (balanceOf[msg.sender] < amount) throw;               // checks if it has enough to sell
        balanceOf[msg.sender] += amount;                   // adds the amount to buyer's balance
        balanceOf[this] -= amount;                         // subtracts amount from seller's balance
    }

}