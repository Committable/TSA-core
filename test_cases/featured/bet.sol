pragma solidity ^0.4.24;

contract Bet {
   address gameOwner = address(0);
   mapping (address => uint256) public balanceOf;
   bool locked = true;

   function bet() internal {
      if ((random()%2==1) && (!locked)) {
         if (!msg.sender.call.value(4 ether)()) {
            throw;
         }
      }
      balanceOf[msg.sender] -= 2;
   }

   function lock() {
      if (gameOwner==msg.sender) {
        locked = true;
      }
   }

   function unlock() {
      if (gameOwner==msg.sender) {
        locked = false;
      }
   }

   function change_owner(address owner) {
      if (!locked){
        gameOwner = owner;
      }
   }

   function withdrawFunds_4_or_0() payable {
      if (balanceOf[msg.sender] > 2) {
        bet();
      }
   }

   function depositFunds() payable {
      balanceOf[msg.sender] += msg.value;
   }

   function depositFunds(uint256 _value) {
       balanceOf[msg.sender] += _value;
       msg.sender.call.value(_value);
   }

   function random() view returns (uint8) {
      return uint8(uint256(keccak256(block.blockhash(block.number-1), block.difficulty))%256);
    }

   function () public payable {
      bet();
    }
}