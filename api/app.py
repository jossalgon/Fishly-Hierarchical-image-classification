import os
import time
import json
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, session
from flask_session import Session
from PIL import Image
from fastai.vision.all import *
import numpy as np
import uuid
from raven.contrib.flask import Sentry
import operator


UPLOAD_FOLDER = 'images/'
ALLOWED_EXTENSION = ['jpg', 'jpeg']

app = Flask(__name__, static_url_path='/static')
app.secret_key = 'super secret key'
app.config['SESSION_TYPE'] = 'filesystem'

sess = Session()
sess.init_app(app)


app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
sentry = Sentry(app, dsn='XXXXXXXXX')

def custom_get_y(o):
    fine_label = o['Specie']
    coarse1_label = o['Family']
    return [coarse1_label, fine_label]


class Resnet50CustomModel(Module):
    def __init__(self, coarse_encoder, fine_encoder, coarse_head, fine_head):
        self.coarse_stem = coarse_encoder[:4]
        self.coarse_block1 = coarse_encoder[4]
        self.coarse_block2 = coarse_encoder[5]
        self.coarse_block3 = coarse_encoder[6]
        self.coarse_block4 = coarse_encoder[7]
        self.coarse_head = coarse_head

        self.fine_stem = fine_encoder[:4]
        self.fine_block1 = fine_encoder[4]
        self.fine_block2 = fine_encoder[5]
        self.fine_block3 = fine_encoder[6]
        self.fine_block4 = fine_encoder[7]
        self.fine_head = fine_head

    def forward(self, x):
        x_c = self.coarse_stem(x)
        x_f = self.fine_stem(x)
        x_f = x_f + x_c

        x_c = self.coarse_block1(x_c)
        x_f = self.fine_block1(x_f)
        x_f = x_f + x_c

        x_c = self.coarse_block2(x_c)
        x_f = self.fine_block2(x_f)
        x_f = x_f + x_c

        x_c = self.coarse_block3(x_c)
        x_f = self.fine_block3(x_f)

        x_c = self.coarse_block4(x_c)
        x_f = self.fine_block4(x_f)

        coarse1_label = self.coarse_head(x_c)
        fine_label = self.fine_head(x_f)

        return {
            'fine_label': fine_label,
            'coarse1_label': coarse1_label
        }


class CustomCategorize(DisplayedTransform):
    "Reversible transform of category string to `vocab` id"
    loss_func, order = CrossEntropyLossFlat(), 1

    def __init__(self, vocab=None, vocab_coarse1=None, vocab_coarse2=None, sort=True, add_na=False, num_y=1):
        store_attr()
        self.vocab = None if vocab is None else CategoryMap(vocab, sort=sort, add_na=add_na)
        self.vocab_coarse1 = None if vocab_coarse1 is None else CategoryMap(vocab_coarse1, sort=sort, add_na=add_na)

    def setups(self, dsets):
        fine_dsets = [d[1] for d in dsets]
        coarse1_dsets = [d[0] for d in dsets]
        if self.vocab is None and dsets is not None: self.vocab = CategoryMap(fine_dsets, sort=self.sort,
                                                                              add_na=self.add_na)
        if self.vocab_coarse1 is None and dsets is not None: self.vocab_coarse1 = CategoryMap(coarse1_dsets,
                                                                                              sort=self.sort,
                                                                                              add_na=self.add_na)
        self.c = len(self.vocab)

    def encodes(self, o):
        return {'fine_label': TensorCategory(self.vocab.o2i[o[1]]),
                'coarse1_label': TensorCategory(self.vocab_coarse1.o2i[o[0]])
                }

    def decodes(self, o):
        return Category(self.vocab[o])


def CustomCategoryBlock(vocab=None, sort=True, add_na=False, num_y=1):
    "`TransformBlock` for single-label categorical targets"
    return TransformBlock(type_tfms=CustomCategorize(vocab=vocab, sort=sort, add_na=add_na))


def custom_splitter(model):
    return [params(model.coarse_stem),
            params(model.coarse_block1),
            params(model.coarse_block2),
            params(model.coarse_block3),
            params(model.coarse_block4),
            params(model.fine_stem),
            params(model.fine_block1),
            params(model.fine_block2),
            params(model.fine_block3),
            params(model.fine_block4),
            params(model.coarse_head),
            params(model.fine_head)]


def loss_func(out, targ):
    return nn.CrossEntropyLoss(weight=weights)(out['fine_label'], targ['fine_label']) + \
           nn.CrossEntropyLoss(weight=weights_family)(out['coarse1_label'], targ['coarse1_label'])

def custom_accuracy(inp, targ, axis=-1):
    pred1, targ1 = flatten_check(inp['fine_label'].argmax(dim=axis), targ['fine_label'])
    acc1 = (pred1 == targ1).float().mean()
    return acc1

class _ConstantFunc():
    "Returns a function that returns `o`"
    def __init__(self, o): self.o = o
    def __call__(self, *args, **kwargs): return self.o

def get_preds(learn, ds_idx=1, dl=None, with_input=False, with_decoded=False, with_loss=False, act=None,
              inner=False, reorder=True, cbs=None, **kwargs):
    if dl is None: dl = learn.dls[ds_idx].new(shuffled=False, drop_last=False)
    else:
        try: len(dl)
        except TypeError as e:
            raise TypeError("`dl` is something other than a single `DataLoader` object")
    if reorder and hasattr(dl, 'get_idxs'):
        idxs = dl.get_idxs()
        dl = dl.new(get_idxs = _ConstantFunc(idxs))
    cb = GatherPredsCallback(with_input=with_input, with_loss=with_loss, **kwargs)
    ctx_mgrs = learn.validation_context(cbs=L(cbs)+[cb], inner=inner)
    if with_loss: ctx_mgrs.append(learn.loss_not_reduced())
    with ContextManagers(ctx_mgrs):
        learn._do_epoch_validate(dl=dl)
        if act is None: act = getattr(learn.loss_func, 'activation', noop)
        res = cb.all_tensors()
        res[1] = res[1]['fine_label']
        pred_i = 1 if with_input else 0
        if res[pred_i] is not None:
            res[pred_i] = act(res[pred_i])
            if with_decoded: res.insert(pred_i+2, getattr(learn.loss_func, 'decodes', noop)(res[pred_i]))
        if reorder and hasattr(dl, 'get_idxs'): res = nested_reorder(res, tensor(idxs).argsort())
        return tuple(res)
    learn._end_cleanup()



learn = load_learner('models/linked-cnn/species1000/species1000-linkedcnn-exp5-resnet50-fepochs1-uepochs30')

def get_prediction(path, num=None):
    try:
        dl = learn.dls.test_dl([path], num_workers=0)
        inp, preds, _, dec_preds = get_preds(learn, dl=dl, with_input=True, with_decoded=True)
        datas = list(zip(learn.dls.vocab, dec_preds[0]))
        results_with_probs = sorted(datas, key=operator.itemgetter(1), reverse=True)[:num]
        results = [result[0] for result in results_with_probs]
        return results
    except Exception as e:
        sentry.captureException()


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSION


@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/privacy-policy', methods=['GET'])
def privacy():
    return render_template('privacy.html')


@app.route('/classes', methods=['GET'])
def classes():
    return json.dumps(list(learn.dls.vocab))


@app.route('/predict', methods=['GET', 'POST'])
def predict():
    predicted, image_id = None, None
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            return redirect(request.url)
        image_id = str(uuid.uuid1())
        file = request.files['file']
        # if user does not select file, browser also
        # submit a empty part without filename
        if file.filename == '':
            return redirect(request.url)
        if file and allowed_file(file.filename):
            file_path = os.path.join(UPLOAD_FOLDER, image_id+'.jpg')
            file.save(file_path)
            results = get_prediction(file_path, 3)
            predicted = ', '.join(results)
            # os.remove(file_path)

        session['image_id'] = image_id
        session['predicted'] = predicted
        return redirect(request.url)
    return render_template('predict.html', predicted=session.get('predicted'), image_id=session.get('image_id'))


@app.route('/uploads/<filename>')
def send_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


@app.route('/api/predict', methods=['POST'])
def api_predict():
    predicted, image_id = None, None
    # check if the post request has the file part
    if 'file' not in request.files:
        return redirect(request.url)
    image_id = str(uuid.uuid1())
    file = request.files['file']
    # if user does not select file, browser also
    # submit a empty part without filename
    if file.filename == '':
        return redirect(request.url)
    if file and allowed_file(file.filename):
        file_path = os.path.join(UPLOAD_FOLDER, image_id+'.jpg')
        file.save(file_path)
        predicted = get_prediction(file_path)
        # os.remove(file_path)
    return json.dumps({'result': predicted})


if __name__ == "__main__":
    app.run(host="0.0.0.0")
