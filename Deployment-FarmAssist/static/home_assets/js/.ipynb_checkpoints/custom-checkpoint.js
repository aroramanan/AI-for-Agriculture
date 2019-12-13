// Initialise Pusher
const pusher = new Pusher('e0e3f671b7d5cde1dbb6', {
    cluster: 'ap2',
    encrypted: true
});

// Subscribe to movie_bot channel
const channel = pusher.subscribe('KrishiBot');

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

$('#price').on('click', function(e){
        e.preventDefault();
        $.get("/get_price",function(data,status){
            console.log(data);
        });
});



$(function() {
    function submit_message(message) {
 
        $.post( "/send_message", {
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
        submit_message(input_message)
        
        }
        
    }
    
    $('#recorder').on('click', function(e){
        e.preventDefault();
        send_audio()
    });
    
    
});