from flask import Flask, render_template, session
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'veiasai'
socketio = SocketIO(app)

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('login', namespace='/poker')
def login(msg):
    # check pwd
    session['user'] = msg['user']
    emit('login', {'code': 0}, room=session.sid)

if __name__ == '__main__':
    socketio.run(app)