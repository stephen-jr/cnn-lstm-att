import eel
import dill
import pandas as pd
from build import preprocess_text
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.sequence import pad_sequences

model = load_model('models/model_final')
print("======Model Initialized=========")

with open('utils/tokenizer.pkl', 'rb') as f:
    t = dill.load(f)
with open('utils/history_final.pkl', 'rb') as f:
    h = dill.load(f)


@eel.expose
def classify(param):
    _f = pd.DataFrame(param)
    try:
        for key in ["text", "reviewText"]:
            if key in _f.columns:
                _pre = _f[key].astype("str").apply(preprocess_text)
                _t_text = t.texts_to_sequences(_pre)
                _t = pad_sequences(_t_text, padding="post", maxlen=70)
                print("==========Predicting===========")
                _p = model.predict(_t)
                _f['PreprocessedText'] = _pre
                _f['PredictionScores'] = _p
                _f['Polarity'] = ['Positive' if x >= 0.5 else 'Negative' for x in _p]
                _f.to_csv("classification/insight.csv")
                _s = _f.sample(n=10)
                return {
                    'sentences': _s["text"].to_list(),
                    'predictions': _s["PredictionScores"].astype("float").apply(lambda x: round(x, 5)).to_list(),
                    'polarity': _s["Polarity"].to_list(),
                    'insight': _f["Polarity"].value_counts().to_list()
                }
        return {
            "error": "Ensure Uploaded file has a text or review column"
        }
    except BaseException as e:
        print(e)
        return {
            "error": str(e)
        }


eel.init('web')
eel.start('index.html', size=(1024, 700))
