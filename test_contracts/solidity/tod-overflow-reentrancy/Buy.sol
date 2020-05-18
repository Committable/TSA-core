contract TransactionOrdering {
    uint256 price;
    address owner;
    function changeowner(address adr){
        owner = adr;
    }
    function ca(){
        owner.call.value(1)();
    }
}