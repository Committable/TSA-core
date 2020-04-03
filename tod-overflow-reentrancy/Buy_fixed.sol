contract TransactionOrdering {
    uint256 price;
    address owner;
    bool flag;

    event Purchase(address _buyer, uint256 _price);
    event PriceChange(address _owner, uint256 _price);

    modifier ownerOnly() {
        require(msg.sender == owner);
        _;
    }

    function TransactionOrdering() {
        // constructor
        owner = msg.sender;
        price = 100;
    }

    function buy() returns (uint256) {
        if(flag == true){
            msg.sender.transfer(price);
            }
        return price;
    }

    function setPrice(uint256 _price) ownerOnly() {
        if(flag == false){
            price = _price;
            flag = true;
         }
        PriceChange(owner, price);
    }
}