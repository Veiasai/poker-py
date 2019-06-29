from flask import Flask, render_template, session
from flask_socketio import SocketIO, emit, join_room, leave_room
from game import Game
# from werkzeug.contrib.fixers import CGIRootFix

def observerHook(game, action, playerPos, body):
    emit('observer', {'action': action, 'playerPos': playerPos, 'body': body}, room='ob')

app = Flask(__name__)
app.config['SECRET_KEY'] = 'veiasai'
# app.wsgi_app = CGIRootFix(app.wsgi_app)
socketio = SocketIO(app)
game = Game(6)
game.setOb(observerHook)



def newWsHook(sid):
    def Hook(game, action, playerPos, body):
        socketio.emit('player', {'action': action, 'playerPos': playerPos, 'body': body}, room=sid, namespace='/')
    return Hook

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def connect():
    join_room('ob')

@socketio.on('login')
def login(msg):
    session['user'] = msg['user']
    emit('login', {'code': 0, 'body': game.getJSON()}, room=session.get('sid'))

@socketio.on('JOIN')
def join(msg):
    if session['user'] == None:
        emit('JOIN', {'code': -1})
    else:
        r = game.setPlayer(msg['pos'], 500, newWsHook(session.get('sid')))
        session['pos'] = msg['pos']
        leave_room('ob')
        if r != 0:
            emit('JOIN', {'code': -1})

@socketio.on('READY')
def ready(msg):
    pos = session['pos']
    if pos == None:
        emit('READY', {'code': -1})
    else:
        r = game.setReady(pos)
        game.start()
        if r != 0:
            emit('READY', {'code': -1})

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port='30461')