contract test_branch{

    uint256 public sellPrice;
    uint256 public buyPrice;

    function setPrices(uint256 newSellPrice, uint256 newBuyPrice) {
        if (newSellPrice > 10){
            sellPrice = newSellPrice;
        }else{
            sellPrice = 10;
        }

        buyPrice = sellPrice * newBuyPrice;
    }

}