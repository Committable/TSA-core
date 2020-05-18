contract Auction{

 address public currentLeader;

 uint256 public highestBid;




 function bid() public payable{


     require(msg.value > highestBid);

     require(currentLeader.send(highestBid));


  currentLeader = msg.sender;

  highestBid = uint256(currentLeader);

 }

}