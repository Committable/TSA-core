contract Lottery {
    event GetBet(uint betAmount, uint blockNumber, bool won); 

    struct Bet {
        uint betAmount;
        bool won;
    }

    address private organizer;
    Bet[] private bets;

    // Create a new lottery with numOfBets supported bets.
    function Lottery() {
        organizer = msg.sender;
    }
    
    // Fallback function returns ether
    function() {
        throw;
    }
    
    // Make a bet
    function makeBet() {
        // Won if block number is even
        // (note: this is a terrible source of randomness, please don't use this with real money)
        bytes32 randomHash =  keccak256(block.number,0,0);
        bool won = ((uint(randomHash) % 2) == 0);
        
        
        
        // Payout if the user won, otherwise take their money
        if(won) { 
            bets[0]=Bet(msg.value, false);
        }
    }
    
   
    // Suicide :(
    function destroy() {
        if(msg.sender != organizer) { throw; }
        
        suicide(organizer);
    }
}