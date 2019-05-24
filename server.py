import responder
from collections import defaultdict
from jinja2 import Template
from starlette.websockets import WebSocketState
from starlette.websockets import WebSocketDisconnect


api = responder.API()

__version__ = 'v0.0.1'

sessions = defaultdict(list)

html = """
<!DOCTYPE html>
<html>
    <head>
        <title>{{ room }}</title>
    </head>
    <body>
        <h1>Chat Room ({{ room }})</h1>
        <form action="" onsubmit="sendMessage(event)">
            <input type="text" id="messageText" autocomplete="off"/>
            <button>Send</button>
        </form>
        <ul id='messages'>
        </ul>
        <script>
            var ws = new WebSocket("ws://"+location.host+"/ws?room=default");
            ws.onmessage = function(event) {
                var messages = document.getElementById('messages')
                var message = document.createElement('li')
                var content = document.createTextNode(event.data)
                message.appendChild(content)
                messages.appendChild(message)
            };
            function sendMessage(event) {
                var input = document.getElementById("messageText")
                ws.send(input.value)
                input.value = ''
                event.preventDefault()
            }
        </script>
    </body>
</html>
"""


async def broadcast_message(room_sessions, msg):
    for s in room_sessions:
        if s.client_state == WebSocketState.CONNECTED:
            await s.send_json(msg)
        elif s.client_state == WebSocketState.DISCONNECTED:
            room_sessions.remove(s)


@api.route("/")
async def room(req, resp):
    room = req.params.get('room', 'default')
    resp.html = Template(html).render(**locals())


@api.route('/ws', websocket=True)
async def websocket(ws):
    await ws.accept()

    room = ws.query_params["room"]

    sessions[room].append(ws)

    await broadcast_message(sessions[room], "Has new user join room")

    while True:
        try:
            msg = await ws.receive_text()
        except WebSocketDisconnect as e:
            break

        # Broadcast
        await broadcast_message(sessions[room], msg)

    sessions[room].remove(ws)
    await ws.close()


if __name__ == '__main__':
    api.run(address='0.0.0.0')
