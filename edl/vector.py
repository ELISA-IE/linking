import functools
from configparser import ConfigParser
from pymongo import MongoClient
import _pickle as cPickle
import numpy as np


config_path = 'global.conf'
config = ConfigParser()
config.read(config_path)
host = config.get('mongodb', 'host')
port = config.getint('mongodb', 'port')
db_name = config.get('mongodb', 'emb')
client = MongoClient(host=host, port=port)
db = client[db_name]
collection_entity_emb = db['entity_embeddings']
collection_word_emb = db['word_embeddings']
_W = cPickle.loads(db['misc'].find_one({'item': 'W'})['vector'])
_b = cPickle.loads(db['misc'].find_one({'item': 'b'})['vector'])


@functools.lru_cache(maxsize=None)
def get_word_vector(word):
    query = {'item': word}
    response = collection_word_emb.find_one(query)
    if response:
        return cPickle.loads(response['vector'])
    return None


@functools.lru_cache(maxsize=None)
def get_entity_vector(kbid):
    query = {'item': 'en.wikipedia.org/wiki/%s' % kbid}
    response = collection_entity_emb.find_one(query)
    if response:
        return cPickle.loads(response['vector'])
    return None


@functools.lru_cache(maxsize=None)
def get_text_vector(text):
    if not text:
        return None
    vectors = []
    for i in text:
        vec = get_word_vector(i.lower())
        if vec is not None:
            vectors.append(vec)
    if not vectors:
        return None

    ret = np.mean(vectors, axis=0)
    ret = np.dot(ret, _W)
    ret += _b
    ret /= np.linalg.norm(ret, 2)
    return ret
