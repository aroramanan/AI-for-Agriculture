// Initialise Pusher
const pusher = new Pusher('e0e3f671b7d5cde1dbb6', {
    cluster: 'ap2',
    encrypted: true
});

// Subscribe to movie_bot channel
const channel = pusher.subscribe('KrishiBot');
var nearest_market = ''
var price_data=''
var crop=''
// bind new_message event to movie_bot channel
channel.bind('new_message', function(data) {
    console.log(data)
    // Append human message
    $('.chat-container').append(`
        <div class="chat-message col-md-5 human-message">
            ${data.human_message}
        </div>
    `)
    
    // Append bot message
    $('.chat-container').append(`
        <div class="chat-message col-md-5 offset-md-7 bot-message">
        ${data.bot_message}
        </div>
    `)
});

function showPosition(position) {
        $.post( "/send_geolocation", {
            lat: position.coords.latitude, 
            long: position.coords.longitude
        });
        console.log('lat');
        var lat = position.coords.latitude + ','+ position.coords.longitude;
        console.log(lat);
}

$(document).ready(function() {
    if (navigator.geolocation) {
            console.log('loc');
            navigator.geolocation.getCurrentPosition(showPosition);
        }
});

$(function() {
    var crop=''
    function submit_message(message) {
 
        $.post( "/send_message", {
            crop:crop,
            message: message, 
            socketId: pusher.connection.socket_id
        }, handle_response);
        
        function handle_response(data) {
            // append the bot repsonse to the div
            console.log(data.message)
            $('.chat-container').append(`
                <div class="chat-message col-md-5 offset-md-7 bot-message">
                    ${data.message}
                </div>
            `)
            // remove the loading indicator
            $( "#loading" ).remove();
        }
    }
    
    
    $('#target').on('submit', function(e){
        e.preventDefault();
        const input_message = $('#input_message').val()
        // return if the user does not enter any text
        if (!input_message) {
            return
        }
        
        $('.chat-container').append(`
            <div class="chat-message col-md-5 human-message">
                ${input_message}
            </div>
        `)
        
        // loading 
        $('.chat-container').append(`
            <div class="chat-message text-center col-md-2 offset-md-10 bot-message" id="loading">
                <b>...</b>
            </div>
        `)
        
        // clear the text input 
        $('#input_message').val('')
        
        // send the message
        submit_message(input_message)
    });
    

    function send_audio(){
        console.log('1')
        $.post( "/send_audio", {
            socketId: pusher.connection.socket_id
        },display_response);
        
        function display_response(data) {
            // append the bot repsonse to the div
            console.log(data.input)
            $('.chat-container').append(`
        <div class="chat-message col-md-5 human-message">
            ${data.input}
        </div>
    `)
        
        // loading 
        $('.chat-container').append(`
            <div class="chat-message text-center col-md-2 offset-md-10 bot-message" id="loading">
                <b>...</b>
            </div>
        `)
            
        // send the message
        submit_message(data.input)
        
        }
        
    }
    
    $('#recorder').on('click', function(e){
        e.preventDefault();
        send_audio()
    });


    function get_price(){
        id = $('#market').val();
        var market = nearest_market['market'][id]
        var comm = $('#commodity').val();
        $.post( "/get_price", {
            market: market, 
            commodity: comm
        },handle_data);

        function handle_data(data){
            console.log(data);
            price_data=data;          
            len = Object.values(data["VARIETY"]).length;
            $('#pricetable tbody').empty()
            for(var i=0;i<len;i++){
                $('#pricetable').append("<tr><td>"+data['VARIETY'][i]+"</td>"+"<td>"+data['MIN_PRICE'][i]+"</td>"+"<td>"+data['MAX_PRICE'][i]+"</td>"+"<td>"+data['MODAL_PRICE'][i]+"</td></tr>")
            }
            $('#tableModal').modal('show');
            
            $('#myModal').modal('hide');
            
        }

    }
    

    $('#submit').on('click', function(e){
        e.preventDefault();
        get_price();
    });


    $('.price').on('click', function(e){
        e.preventDefault();
        $.get( "/get_market",function(data,status){
            console.log(data);
            nearest_market = data;
            $("#market").empty();
            for( var i = 0; i<5; i++){
                var market = data['market'][i];
                $("#market").append("<option value='"+i+"'>"+market+"</option>");
                }
            commodity = data['commodity'][0];
            len = commodity.length;
            if(len > 10){
                len = 10;
            }
            $("#commodity").empty();
            for( var i = 0; i<len; i++){
                $("#commodity").append("<option value='"+commodity[i]+"'>"+commodity[i]+"</option>");
            }
            $('#myModal').modal('show');
        });
        
        //window.location.href = 'display_price'
    });

    $('#cropsubmit').on('click', function(e){
        e.preventDefault();
        var value = $('#crop').val();
        crop = value;
        $('#buttonModal').modal('hide');

    });

    $("#market").change(function(){
        var id = $(this).val();
        commodity = nearest_market['commodity'][id];
        len = commodity.length;
        if(len > 10){
            len = 10;
        }
        len = commodity.length;
        $("#commodity").empty();
        for( var i = 0; i<len; i++)
        {
            $("#commodity").append("<option value='"+commodity[i]+"'>"+commodity[i]+"</option>");
        }
    });

    $('.krishi').ready(function() {
        $('#buttonModal').modal('show');
    });
    
    $('.chat').on('click', function(e){
        e.preventDefault();
        window.location.href = 'display_chatbot'
    });
    
});