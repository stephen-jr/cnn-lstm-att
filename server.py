import os
import json
import shlex
import subprocess
from flask_cors import CORS
# import keras.backend as k
from flask import Flask, request, render_template, Response, jsonify

process = None
model = None
# template_dir = os.path.abspath('web')


def event_stream(system_command, **kwargs):
    # k.clear_session()
    popen = subprocess.Popen(
        shlex.split(system_command),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        start_new_session=True,
        encoding='windows-1252',
        **kwargs)
    global process
    process = popen
    for stdout_line in iter(popen.stdout.readline, ""):
        try:
            stream_obj = {
                'execution': True,
                'response': stdout_line.strip()
            }
            yield "data: {}\n\n".format(json.dumps(stream_obj))

        except BaseException as e:
            exit(e)
            continue

    popen.stdout.close()
    yield "data: {}\n\n".format(json.dumps({'execution': False}))


app = Flask(__name__, template_folder='web', static_folder='web/static')
CORS(app)
app.debug = True


@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')


@app.route('/upload.html', methods=['GET'])
def upload():
    return render_template('upload.html')


@app.route('/train.html', methods=['GET'])
def train_template():
    return render_template('train.html')


@app.route('/train', methods=['POST'])
def train():
    print(request)
    # return Response(event_stream('py build.py --train '), mimetype="text/event-stream")


@app.route('/classify', methods=['GET'])
def classify():
    global model
    if model is None:
        pass  # load model

    try:
        pass  # run classification

    except BaseException as e:
        exit(e)

app.run()