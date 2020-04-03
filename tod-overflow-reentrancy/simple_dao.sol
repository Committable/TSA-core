
contract SimpleDAO {
  mapping (address => uint) public credit;
  address owner;
    
  function donate(address to) payable public{
    credit[to] += msg.value;
  }
    
  function withdraw(uint amount) public{

      owner = msg.sender;
      require(owner.call.value(amount)());
  }  

  function queryCredit(address to)  public returns(uint){
    return credit[to];
  }
}
