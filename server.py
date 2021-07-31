import os
import json
import dill
import shlex
import subprocess
import pandas as pd
import keras.backend as k
from flask_cors import CORS
from datetime import datetime
from build import preprocess_text
from tensorflow.keras.models import load_model
from flask import Flask, request, render_template, Response, jsonify
from tensorflow.keras.preprocessing.sequence import pad_sequences

process, model, tokenizer, subprocess_data = (None,)*4

def error(msg):
    return jsonify({
        'error': msg
    })

def event_stream(system_command, **kwargs):
    k.clear_session()
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
            # with open("models/"+ _dir + "-logs.txt", "a") as f:
            #     f.write(res + "\n")
            stream_obj = {
                'execution': True,
                'response': stdout_line.strip()
            }
            yield "data: {}\n\n".format(json.dumps(stream_obj))

        except BaseException as e:
            exit(e)

    popen.stdout.close()
    yield "data: {}\n\n".format(json.dumps({'execution': False}))


app = Flask(__name__, template_folder='web', static_folder='web/static')
CORS(app)


@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')


@app.route('/upload.html', methods=['GET'])
def upload():
    return render_template('upload.html')


@app.route('/train.html', methods=['GET'])
def train_template():
    return render_template('train.html')


@app.route('/train', methods=['GET', 'POST'])
def train():
    global subprocess_data
    if request.method == "POST":
        subprocess_data = request.json
        with open('tmp/'+ subprocess_data['fileName'], 'w') as f:
            f.write(json.dumps(subprocess_data['data']))
        return jsonify({
            'info': 'Data received successfully'
        });
    elif request.method == "GET" and subprocess_data is not None:
        date = datetime.now()
        date = date.strftime("%d%m%Y|%H:%M:%S")
        s = subprocess_data['fileName'].split('.')[0] + ' - ' + date
        print('====Training Initialized====')
        f = 'py build.py --train --from-temp {} {}'.format(subprocess_data['fileName'], s)
        return Response(event_stream(f), mimetype="text/event-stream")
        res = {}
        if os.path.exists("models/" + s):
            res = { 'info': 'Training Completed Successfully',
                    'directory': "models/"+ s 
                }
            os.remove('tmp/'+subprocess_data['fileName'])
            subprocess_data = None
        else: 
            res = error("Training failed. Directory not generated");
        return Response("data: {}\n\n".format(json.dumps(res)), mimetype='text/event-stream');
    else: 
        return error("Invalid Subprocess Data");


@app.route('/classify', methods=['POST'])
def classify():
    if request.json:
        global model, tokenizer
        if model is None:
            model = load_model('models/model_final')
        if tokenizer is None:
            with open('utils/tokenizer.pkl', 'rb') as f:
                tokenizer = dill.load(f)
        try:
            _f = pd.DataFrame(request.json['data'])
            for key in ["text", "reviewText"]:
                if key in _f.columns:
                    try:
                        _pre = _f[key].astype("str").apply(preprocess_text)
                        _t_text = tokenizer.texts_to_sequences(_pre)
                        _t = pad_sequences(_t_text, padding="post", maxlen=70)
                        print("==========Predicting===========")
                        _p = model.predict(_t)
                        _f['PreprocessedText'] = _pre
                        _f['PredictionScores'] = _p
                        _f['Polarity'] = ['Positive' if x >= 0.5 else 'Negative' for x in _p]
                        _f.to_csv("classification/"+ request.json['fileName'] +".csv")
                        _s = _f.sample(n=10)
                        return jsonify({
                            'sentences': _s["text"].to_list(),
                            'predictions': _s["PredictionScores"].astype("float").apply(lambda x: round(x, 5)).to_list(),
                            'polarity': _s["Polarity"].to_list(),
                            'insight': _f["Polarity"].value_counts().to_list()
                        })
                    except KeyError as e:
                        continue
                else:
                    continue
            return error("Ensure Uploaded file has a text or reviewText column")
        except BaseException as ex:
            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            message = template.format(type(ex).__name__, ex.args)
            return error( message )
    else:
        return error("Invalid request data")

@app.route('/terminate', methods=['GET'])
def terminate():
    global process
    if process is not None:
        process.terminate()
        process = None
        return jsonify({
            'info': 'Subprocess Terminated Successfully'
        })
    else:
        return jsonify({
            'info': "No subprocess is active at the moment"
        })
if __name__ == '__main__':
    app.run(debug=True)