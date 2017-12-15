import sys
import os
import logging
import ujson as json
from collections import defaultdict
from edl import linker
from edl import cluster
from edl import translator
from edl import util
from edl.models.text import EntityMention, NominalMention, Entity
sys.path.append('/nas/data/m1/panx2/code/amr-reader/amrreader')
from src import reader
from src import ne


def process_mention(mention, lang='en', etype=None):
    em = EntityMention(mention)
    if lang != 'en':
        em.translations = translator.get_translation(em.text, lang)
    linker.add_candidate_entities(em, lang=lang)
    linker.rank_candidate_entities(em, etype=etype)

    lres = []
    for ce in em.candidates:
        lres.append(
            {
                'kbid': ce.kbid,
                'confidence': ce.confidence,
            }
        )
    res = {
        'mention': em.text,
        'type': etype,
        'language': lang,
        'translation': em.translations,
        'results': lres,
    }
    return res


def process_bio(bio, lang='en'):
    entitymentions = util.read_tac_bio_format(bio)
    for em in entitymentions:
        if lang != 'en':
            em.translations = translator.get_translation(em.text, lang)

        rankings = []
        if lang == 'en':
            rankings = ['CONTEXT_SIMILARITY']
        linker.add_candidate_entities(em, lang=lang)
        linker.rank_candidate_entities(em, etype=em.etype, rankings=rankings)

    tab = util.get_tac_tab_format(entitymentions, add_trans=True)
    util.add_tac_runid_and_mid(tab, runid='elisa-ie', mid_prefix='elisa-ie')
    res = '\n'.join(['\t'.join(i) for i in tab])
    return res


def process_amr(raw_amr):
    sents = reader.main(raw_amr)
    ne.add_named_entity(sents)
    sent = sents[0]
    res = {}
    for i in sent.named_entities:
        ne_obj = sent.named_entities[i]
        em = EntityMention(ne_obj.entity_name,
                           text_tok=ne_obj.entity_name.split(),
                           context=sent.sent.split(),
                           etype=ne_obj.maintype)
        # rankings = []
        rankings = ['CONTEXT_SIMILARITY']
        linker.add_candidate_entities(em)
        linker.rank_candidate_entities(em, etype=em.etype, rankings=rankings)
        res[i] = em.entity.kbid if em.entity else '-'
    return res
