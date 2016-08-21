var mafia = {};  // global namespace for persistent data

$(document).ready(function(){
    var ws_scheme = window.location.protocol == "https:" ? "wss" : "ws";
    var webSocket = new WebSocket(ws_scheme + '://' + location.host + location.pathname);

    var chat_message = function(data) {
        var time = new Date(data['timestamp']);
        time = '[' + time.getHours() + ':' + time.getMinutes() + ']';

        var meta = time + ' ' + data['sender'];
        if (data['highlight'])
            meta += ' >>' + data['highlight'];
        meta += ': ';

        meta = $('<span />').text(meta);

        var msg = $('<p />');
        if (data['sender'] === 'System') {
            msg.addClass('message-system');
        } else {
            meta.addClass('message-meta');
        }

        msg.append(meta)
           .append(document.createTextNode(data.text));

        var chat = $('#messages');
        chat.append(msg);
        chat.scrollTop(chat[0].scrollHeight);
    };

    var game_players = function(data) {
        var player_list = $('#chat-members');
        player_list.empty();

        var player;
        for (var p in data['players']) {
            player = $('<p />').text(p);
            player_list.append(player);
        }
    };

    var user_status = function(data) {
        mafia.user_status = data;
    };

    webSocket.onmessage = function(message) {
        var data = JSON.parse(message.data);

        if (data['text']) {
            chat_message(data);
        } else if (data['players']) {
            game_players(data);
        } else if (data['user']) {
            user_status(data)
        }
    };

    $('#msg-form').submit(function(event) {
        var msg = JSON.stringify({
            command: 'chat_msg',
            text: $('#msg').val()
        });
        webSocket.send(msg);

        this.reset();
        event.preventDefault();
    });
});