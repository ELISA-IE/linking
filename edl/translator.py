import functools
from configparser import ConfigParser
from collections import defaultdict
from pymongo import MongoClient


config_path = 'global.conf'
config = ConfigParser()
config.read(config_path)
host = config.get('mongodb', 'host')
port = config.getint('mongodb', 'port')
db_name = config.get('mongodb', 'dict')
client = MongoClient(host=host, port=port)
db = client[db_name]


@functools.lru_cache(maxsize=None)
def get_translation(text, lang):
    query = {'lemma': text}
    collection = db[lang]
    response = collection.find(query)
    count = defaultdict(int)
    for i in response:
        count[i['gloss']] += i['priority']
    res = [i for i, c in sorted(count.items(),
                                key=lambda x: x[1], reverse=True)]
    return res
