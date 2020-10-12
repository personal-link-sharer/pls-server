from flask import Flask
from flask_socketio import SocketIO, emit
from os import path, environ
from datetime import datetime, timedelta
import json
import string


posts_file = 'data/posts.json'
time_format = '%Y-%m-%d_%H:%M:%S'

secret_token = ""
if 'SECRET_TOKEN' in environ:
    secret_token = environ['SECRET_TOKEN']

delete_after_days = 7
if 'DELETE_AFTER_DAYS' in environ:
    delete_after_days = int(environ['DELETE_AFTER_DAYS'])

app = Flask(__name__)
socketio = SocketIO(app, path='/' + secret_token)

def remove_outdated_posts(file_content):
    if file_content == {}:
        return {}

    now = datetime.now()

    new_content = [post for post in file_content['posts'] if (now - datetime.strptime(post['timestamp'], time_format)).days < delete_after_days]
    new_content = {'posts': new_content}

    return new_content

def get_all_posts():
    if not path.isfile(posts_file) or path.getsize(posts_file) == 0:
        return {}
    data = {}
    with open(posts_file) as json_file:
            data = json.load(json_file)

    new_data = remove_outdated_posts(data)

    if new_data != data:
        with open(posts_file, 'w') as outfile:
            json.dump(new_data, outfile)

    return new_data['posts']

@socketio.on('connect')
def connect():
    emit('all_posts', {'data': get_all_posts()})

@socketio.on('remove_id')
def remove_id(json_in, methods=['GET', 'POST']):
    data = {}

    with open(posts_file) as json_file:
        data = json.load(json_file)
    
    if data == {}:
        return

    new_data = [post for post in data['posts'] if post['id'] != int(json_in['id'])]
    new_data = {'posts': new_data}

    with open(posts_file, 'w') as outfile:
        json.dump(new_data, outfile)
    
    socketio.emit('id_removed', int(json_in['id']))

@socketio.on('send_post')
def receive_post(json_in, methods=['GET', 'POST']):
    data = {}

    # if file not yet exists: create new
    if not path.isfile(posts_file):
        data['posts'] = []
    
    # otherwise append
    else:
        with open(posts_file) as json_file:
            data = json.load(json_file)

    # find valid id
    i = 1
    for p in data['posts']:
        if p['id'] >= i:
            i = p['id'] + 1

    new_url = {'id': i,
        'timestamp': datetime.now().strftime(time_format),
        'type': json_in['type'],
        'content': json_in['data']}

    data['posts'].append(new_url)

    with open(posts_file, 'w') as outfile:
        json.dump(data, outfile)
    
    socketio.emit('new_post', new_url)


if __name__ == '__main__':    
    hex_digits = set(string.hexdigits)
    
    # check if secret token is set
    if secret_token == '':
        print("ENVVAR 'SECRET_TOKEN' is not set. Quitting...")
    # check if secret token is correct type (hex)
    elif not all(c in hex_digits for c in secret_token):
        print("ENVVAR 'SECRET_TOKEN' is invalid format. Must be hexadecimal digits. Quitting...")
    elif not isinstance(delete_after_days, int):
        print("ENVVAR 'DELETE_AFTER_DAYS' is invalid format. Must be digits only - NOT string. Quitting...")
    else:
        socketio.run(app, host='0.0.0.0')
    