contract test{
    address owner;
    address my;
    int a;
    function overflow(int x){
        a = a+x;
    }
    function reentrancy(address myaddress){
        myaddress.call.value(1)();
    }

    function changemy(address taint){
        my = taint;
    }

    function callme(){
        my.call.value(1)();
    }
}