import sys
from flask import Flask, request, jsonify
import ujson as json
import api


app = Flask(__name__)


@app.route('/linking', methods=["GET"])
def linking():
    args = request.args
    for i in ['mention', 'lang']:
        try:
            assert i in args
        except AssertionError:
            return 'ERROR: Missing argument: %s' % i

    mention = request.args.get('mention')
    lang = request.args.get('lang')
    etype = request.args.get('type') if 'type' in request.args else None
    res = api.process_mention(mention, lang, etype=etype)
    return jsonify(res)


@app.route('/linking_bio', methods=["POST"])
def linking_bio():
    form = request.form
    for i in ['bio_str', 'lang']:
        try:
            assert i in form
        except AssertionError:
            return 'ERROR: Missing argument: %s' % i

    bio_str = request.form.get('bio_str')
    lang = request.form.get('lang')
    try:
        res = api.process_bio(bio_str, lang)
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        msg = 'unexpected error: %s %s %s' % \
              (exc_type, exc_obj, exc_tb.tb_lineno)
        return msg
    return res


@app.route('/linking_amr', methods=["POST"])
def linking_amr():
    form = request.form
    for i in ['amr_str']:
        try:
            assert i in form
        except AssertionError:
            return 'ERROR: Missing argument: %s' % i

    amr_str = request.form.get('amr_str')
    try:
        res = api.process_amr(amr_str)
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        msg = 'unexpected error: %s %s %s' % \
              (exc_type, exc_obj, exc_tb.tb_lineno)
        return msg
    return jsonify(res)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('USAGE: <PORT>')
        sys.exit()
    app.run('0.0.0.0', port=int(sys.argv[1]), threaded=True)
