import re
import sys
import json

import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix

import time
import tensorflow as tf
import matplotlib as mpl
import matplotlib.pyplot as plt
from tensorflow.keras.callbacks import EarlyStopping
from tensorflow.keras.preprocessing.text import Tokenizer
from tensorflow.keras.preprocessing.sequence import pad_sequences
from tensorflow.keras.layers import Concatenate, Dense, Input, LSTM, Embedding
from tensorflow.keras.layers import Dropout, Bidirectional, Conv1D
from tensorflow.keras.layers import Layer, MaxPooling1D
from tensorflow.keras.models import Model
from tensorflow.keras.metrics import Precision, Recall, AUC, BinaryAccuracy


def preprocess_text(v):
    v = re.sub(r'http\S+', ' ', v)
    v = re.sub(r'@\w+', ' ', v)
    v = re.sub(r'pic.\S+', ' ', v)
    v = re.compile(r'<[^>]+>').sub(' ', v)
    v = re.sub('[^a-zA-Z]', ' ', v)
    v = re.sub(r"\s+[a-zA-Z]\s+", ' ', v)
    v = re.sub(r'RT', ' ', v)
    v = re.sub(r'\s+', ' ', v)
    return v.strip()


def plot_metrics(hist):
    m = [
        "loss",
        "accuracy",
        "precision", "recall",
        "auc",
    ]
    for n, m in enumerate(m):
        name = m.replace("_", " ").capitalize()
        plt.subplot(5, 2, n + 1)
        plt.plot(
            hist.epoch,
            hist.history[m],
            color=colors[0],
            label="Train",
        )
        plt.plot(
            hist.epoch,
            hist.history["val_" + m],
            color=colors[1],
            linestyle="--",
            label="Val",
        )
        plt.xlabel("Epoch")
        plt.ylabel(name)
        if m == "loss":
            plt.ylim([0, plt.ylim()[1] * 1.2])
        elif m == "accuracy":
            plt.ylim([0.4, 1])
            plt.ylim([0, plt.ylim()[1]])
        elif m == "precision":
            plt.ylim([0, 1])
        elif m == "recall":
            plt.ylim([0.4, 1])
        else:
            plt.ylim([0, 1])

        plt.legend()
        plt.savefig("Training History.png")


def plot_cm(labels, predictions):
    cm = confusion_matrix(labels, predictions)
    plt.figure(figsize=(5, 5))
    sns.heatmap(cm, annot=True, fmt="d")
    plt.title("Confusion matrix (non-normalized))")
    plt.ylabel("Actual label")
    plt.xlabel("Predicted label")
    plt.savefig("confusion matrix.png")


class BAttention(Layer):
    def __init__(self, units):
        super(BAttention, self).__init__()
        self.W1 = tf.keras.layers.Dense(units)
        self.W2 = tf.keras.layers.Dense(units)
        self.V = tf.keras.layers.Dense(1)

    def call(self, query, values):
        query_with_time_axis = tf.expand_dims(query, 1)
        score = self.V(tf.nn.tanh(self.W1(query_with_time_axis) + self.W2(values)))
        attention_weights = tf.nn.softmax(score, axis=1)
        context_vector = attention_weights * values
        context_vector = tf.reduce_sum(context_vector, axis=1)

        return context_vector, attention_weights


if __name__ == '__main__':
    metrics = [
        BinaryAccuracy(name='accuracy'),
        Precision(name='precision'),
        Recall(name='recall'),
        AUC(name='auc'),
    ]

    args = sys.argv
    if args[1] == '--train' and args[2]:
        json_string = args[2]
        json_string = json.loads(json_string)
        df = pd.DataFrame.from_dict(json_string, orient='index')
        df.reset_index(level=0, inplace=True)
        print( df.head() )
        exit()
        # df = pd.read_json("Musical_Instruments_5.json", lines=True)
        X = df.reviewText.astype('str').apply(preprocess_text)
        Y = pd.get_dummies(df.overall).values
        sequence_length = [len(x.split(" ")) for x in X]
        maxlen = int(np.mean([np.mean(sequence_length), np.median(sequence_length)]))
        X_train, X_test, Y_train, Y_test = train_test_split(X, Y, test_size=0.3, random_state=42)

    # Tokenize sentences
    print("Tokenizing words ...... ")
    start = time.time()
    tokenizer = Tokenizer(50000)
    tokenizer.fit_on_texts(X)
    X_train = tokenizer.texts_to_sequences(X_train)
    X_test = tokenizer.texts_to_sequences(X_test)
    vocab_size = len(tokenizer.word_index) + 1
    print("Found {} unique words".format(vocab_size))
    print('Time taken : {}s'.format(time.time() - start))
    print('Padding Sentences')
    start = time.time()
    X_train = pad_sequences(X_train, padding='post', maxlen=maxlen)
    X_test = pad_sequences(X_test, padding='post', maxlen=maxlen)
    print('Time taken : {}s'.format(time.time() - start))

    X_train = np.asarray(X_train)
    X_test = np.asarray(X_test)
    Y_train = np.asarray(Y_train)
    Y_test = np.asarray(Y_test)

    sequence_input = Input(shape=(maxlen,), dtype='int32')
    embedding_layer = Embedding(vocab_size, 100)(sequence_input)
    cnn_layer = Conv1D(16, 2, activation="relu", padding="same")(embedding_layer)
    max_pool = MaxPooling1D()(cnn_layer)
    lstm = Bidirectional(LSTM(32, return_sequences=True))(max_pool)
    l_output, f_h, f_c, b_h, b_c = Bidirectional(LSTM(32, return_sequences=True, return_state=True))(max_pool)
    state = Concatenate()([f_h, b_h])
    c_v, _att = BAttention(20)(state, l_output)
    dense = Dense(16, activation='relu')(c_v)
    dropout = Dropout(0.3)(dense)
    output = Dense(5, activation="softmax")(dropout)

    model = Model(inputs=sequence_input, outputs=output)
    model.compile(loss="categorical_crossentropy", optimizer="adam", metrics=metrics)
    model.summary()

    es = EarlyStopping(monitor='val_loss', mode='min', patience=2, verbose=1)
    history = model.fit(
        X_train,
        Y_train,
        epochs=10,
        verbose=True,
        validation_data=(X_test, Y_test),
        batch_size=100,
        callbacks=[es]
    )

    training_time = time.time() - start
    print("Training Time : ", training_time)
    _, t_acc, t_pre, t_rec, t_auc = model.evaluate(X_test)

    model.save("att_model")

    colors = plt.rcParams["axes.prop_cycle"].by_key()["color"]
    mpl.rcParams["figure.figsize"] = (12, 18)
    plot_metrics(history)

    prediction = model.predict(X_test)
    y_pred = (prediction > 0.5)
    report = classification_report(Y_test, y_pred)
    print(report)
    plot_cm(np.array([np.argmax(x) for x in Y_test]), np.array([np.argmax(x) for x in y_pred]))
