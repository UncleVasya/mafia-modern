var mafia = {};  // global namespace for persistent data

$(document).ready(function(){
    var ws_scheme = window.location.protocol == "https:" ? "wss" : "ws";
    var webSocket = new WebSocket(ws_scheme + '://' + location.host);

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

    var chat_members = function(data) {
        var mem_list = $('#chat-members');
        mem_list.empty();

        var members = data['chat_members'];
        $('#chat-members-num').text(members.length.toString());

        var member;
        for (var i=0; i < members.length; ++i) {
            member = $('<p />').text(members[i]);
            mem_list.append(member);
        }
    };

    var game_list = function(data) {
        var games_table = $('#games-table').find('tbody');
        games_table.empty();

        var games = data['game_list'];
        var game, game_row, players, player;
        for (var i=0; i < games.length; ++i) {
            game = games[i];

            game_row = $('<tr />').addClass('game-row').append(
                $('<td />').text(game['id']).hide(),
                $('<td />').text(game['name']),
                $('<td />').text(game['players_num']),
                $('<td />').text(game['level']),
                $('<td />').text(game['players_num'] - Object.keys(game['players']).length)
            );

            players = $('<td />');
            for (player in game['players']) {
                player = $('<span>').text(player);
                players.append(player);
            }
            game_row.append(players);

            games_table.append(game_row);
        }
    };

    // enables or disables game buttons according to user status
    var user_status = function(data) {
        mafia.user_status = data;

        $('.game-button').attr('disabled', 'disabled');
        if (data['game']) {
            $('#game-leave').removeAttr('disabled');
        } else {
            $('#game-create').removeAttr('disabled');
            if (('#games-table').find('.selected')) {
                $('#game-join').removeAttr('disabled');
            }
        }
    };

    webSocket.onmessage = function(message) {
        var data = JSON.parse(message.data);

        if (data['text']) {
            chat_message(data);
        } else if (data['chat_members']) {
            chat_members(data);
        } else if (data['game_list']) {
            game_list(data);
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

    $('#game-create').click(function() {
        var msg = JSON.stringify({
            command: 'game_create'
        });
        webSocket.send(msg);
    });

    $('#game-join').click(function() {
        var games_table = $('#games-table');
        var game_id = games_table.find('.selected :first-child').text();
        game_id = parseInt(game_id);

        var msg = JSON.stringify({
            command: 'game_join',
            id: game_id
        });
        webSocket.send(msg);
    });

    $('#game-leave').click(function() {
        var msg = JSON.stringify({
            command: 'game_leave'
        });
        webSocket.send(msg);
    });

    $('#games-table').on('click', '.game-row', function() {
        $(this).siblings().removeClass('selected');
        $(this).addClass('selected');
        if (!mafia.user_status['game']) {
            $('#game-join').removeAttr('disabled');
        }
    });
});