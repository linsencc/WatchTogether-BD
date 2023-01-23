let Namespace = '/room';
let RoomNumber = null;
let WebsocketUrl = null;

let Socket = null;


function create() {
    let postData = {
        roomNumber: $('#room_number').val()
    }

    console.log('postdata', postData);

    $.ajax({
        url: "http://127.0.0.1:5000/create-room",
        type: 'POST',
        dataType: 'json',
        contentType: 'application/json;charset=UTF-8',
        data: JSON.stringify(postData),
        success: function (res) {
            console.log(res)

            WebsocketUrl = location.protocol + '//' + document.domain + ':' + location.port + Namespace;
            Socket = io.connect(WebsocketUrl);

            Socket.on('connect', function () {
                let data = {
                    url: WebsocketUrl,
                    room_number: RoomNumber,
                    video_state: 0,
                    video_progress: 0,
                }

                Socket.emit('user-init', data);
            });
        },
        error: function (res) {
            console.log(res)
        }
    });

};