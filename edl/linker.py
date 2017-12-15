import functools
from copy import deepcopy
from configparser import ConfigParser
from collections import defaultdict
from pymongo import MongoClient
from scipy.spatial.distance import cosine
from edl.models.text import EntityMention, NominalMention, Entity
from edl import vector


config_path = 'global.conf'
config = ConfigParser()
config.read(config_path)
host = config.get('mongodb', 'host')
port = config.getint('mongodb', 'port')
db_name = config.get('mongodb', 'kb')
client = MongoClient(host=host, port=port)
db = client[db_name]
collection_mention_table = db['mention_table']
collection_etypes = db['etypes']


@functools.lru_cache(maxsize=None)
def get_etype(kbid):
    query = {'kbid': kbid}
    response = collection_etypes.find_one(query)
    if response:
        return response['etype']
    return None


@functools.lru_cache(maxsize=None)
def get_candidate_entities(mention, n):
    res = []
    query = {'mention': mention.lower()}
    response = collection_mention_table.find_one(query)
    if response:
        for kbid, score in response['entities'][:n+1]:
            ce = Entity(kbid, etype=get_etype(kbid))
            ce.vector = vector.get_entity_vector(kbid)
            ce.features = {
                'COMMONNESS': score
            }
            res.append(ce)
    add_etype_commonness(res)
    return res


@functools.lru_cache(maxsize=None)
def get_candidate_entities_multi_mentions(mentions, n):
    res = []
    merged_ce = {}
    for mention in mentions:
        query = {'mention': mention.lower()}
        response = collection_mention_table.find_one(query)
        if response:
            for kbid, score in response['entities'][:n+1]:
                if kbid not in merged_ce:
                    ce = Entity(kbid, etype=get_etype(kbid))
                    ce.vector = vector.get_entity_vector(kbid)
                    ce.features = {
                        'COMMONNESS': score
                    }
                    merged_ce[kbid] = ce
                else:
                    merged_ce[kbid].features['COMMONNESS'] += score
    tol = sum([merged_ce[kbid].features['COMMONNESS'] for kbid in merged_ce])
    for kbid in merged_ce:
        merged_ce[kbid].features['COMMONNESS'] /= tol
        res.append(merged_ce[kbid])
    add_etype_commonness(res)
    return res


def add_etype_commonness(candidate_entities):
    etype_probs = defaultdict(float)
    for ce in candidate_entities:
        etype_probs[ce.etype] += ce.features['COMMONNESS']
    for ce in candidate_entities:
        a = ce.features['COMMONNESS']
        b = etype_probs[ce.etype]
        ce.features['ETYPE_COMMONNESS'] =  a / b


def add_candidate_entities(entitymention, n=10, lang='eng'):
    em = entitymention
    if lang == 'eng':
        query = em.text.lower()
        em.candidates = get_candidate_entities(query, n)
    else:
        gcemm = get_candidate_entities_multi_mentions
        em.candidates = gcemm(tuple(em.translations), n)
        if not em.candidates:
            query = em.text.lower()
            em.candidates = get_candidate_entities(query, n)


def add_salience(entitymention, etype=None):
    em = entitymention
    if etype and etype in ['PER', 'ORG', 'GPE']:
        for ce in em.candidates:
            if ce.etype and ce.etype == etype :
                ce.features['SALIENCE'] = ce.features['ETYPE_COMMONNESS']
            else:
                ce.features['SALIENCE'] = ce.features['COMMONNESS'] * 0.3 # TO-DO: thres
    else:
        for ce in em.candidates:
            ce.features['SALIENCE'] = ce.features['COMMONNESS']


def add_context_similarity(entitymention):
    em = entitymention
    context = tuple(sorted(set(em.context)-set(em.text_tok)))
    em.vector = vector.get_text_vector(context) if context else None
    for ce in em.candidates:
        if em.vector is not None and ce.vector is not None:
            cs = 1 - cosine(em.vector, ce.vector)
            cs = max(cs, 0.0)
            ce.features['CONTEXT_SIMILARITY'] = cs
        else:
            ce.features['CONTEXT_SIMILARITY'] = 0.0


def rank_candidate_entities(entitymention, etype=None, rankings=[]):
    em = entitymention
    add_salience(em, etype=etype)

    if 'CONTEXT_SIMILARITY' in rankings:
        add_context_similarity(em)

    # Ranking
    for ce in em.candidates:
        ce.confidence = ce.features['SALIENCE']
        for r in rankings:
            ce.confidence += ce.features[r]

    # Softmax
    tol = sum([ce.confidence for ce in em.candidates])
    for ce in em.candidates:
        ce.confidence /= tol

    em.candidates = sorted(em.candidates, key=lambda x: x.confidence,
                           reverse=True)
    if em.candidates:
        em.entity = deepcopy(entitymention.candidates[0])







# # Test
# if __name__ == '__main__':
#     for i in get_candidate_entities('Japan', 10):
#         print(i)
#     print()
#     for i in get_candidate_entities_multi_mentions(tuple(['Japan', 'Japanese']), 10):
#         print(i)

# if __name__ == '__main__':
#     a = vector.get_word_vector('football')
#     b = vector.get_entity_vector('en.wikipedia.org/wiki/Apple_Inc.')
#     print(1 - cosine(a, b))
#     print(vector.get_text_vector(tuple('Apple orange and banana'.split())))


if __name__ == '__main__':
    a = EntityMention('apple', etype='ORG')
    a.context = 'is a computer company'.split()
    add_candidate_entities(a)
    rank_candidate_entities(a, etype='ORG', rankings=['CONTEXT_SIMILARITY'])
    print(a)

# if __name__ == '__main__':
#     for i in get_candidate_entities('Al-Shabab', 10):
#         print(i)
