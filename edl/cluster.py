import re
from collections import defaultdict
import jellyfish._jellyfish as jf
import jellyfish
import unidecode
import logging
import ujson as json
from edl.models.text import EntityMention, NominalMention, Entity


logger = logging.getLogger()
logging.basicConfig(format='%(asctime)s: %(levelname)s: %(message)s')
logging.root.setLevel(level=logging.INFO)


class Cluster:
    def __init__(self, name, text, cluster=None):
        self.name = name
        self.text = text
        self.results = []
        if cluster:
            self.merge(cluster)

    def add_result(self, result):
        self.results.append(result)

    def merge(self, cluster):
        self.results.extend(cluster.results)


def nil_clustering(corpus, lang, resources=None,
                   propagate=False, verbose=False):
    # Load resources
    designators = set()
    stop_words = set()
    morph = {}
    if resources:
        if 'morph' in resources:
            pass
            # if lang == 'il5':
            #     for lemma, stem in read_upenn_morph(res['morph']):
            #         morph[lemma] = stem
            # else:
            #     with open(res['morph'], 'r', encoding='utf-8') as r:
            #         for line in r:
            #             source, target, _, _ = line.rstrip('\n').split('\t')
            #             morph[source] = target
        if 'designator' in resources:
            with open(resources['designator'], 'r', encoding='utf-8') as r:
                for line in r:
                    designator = line.rstrip().lower()
                    designators.add(designator)
                    if designator in morph and designator != morph[designator]:
                        designators.add(morph[designator])
        if 'stop_word' in resources:
            stop_words = json.load(open(resources['stop_word']))

    # Create initial clusters
    result_cluster_map = {}
    clusters = {}
    for docid in corpus:
        for result in corpus[docid]:
            mention = result.text
            mention_lower = mention.lower()
            if mention_lower in clusters:
                clusters[mention_lower].add_result(result)
                result_cluster_map[result] = clusters[mention_lower]
            else:
                cluster = Cluster('NIL{:07d}'.format(len(clusters)),
                                  mention_lower)
                cluster.add_result(result)
                clusters[mention_lower] = cluster
                result_cluster_map[result] = clusters[mention_lower]
    logger.info('# initial cluster: {}'.format(len(clusters)))

    # 1. Normalization: remove designators and stopwords, stemming
    new_clusters = {}
    cluster_map = []
    for _, cluster in clusters.items():
        tokens = []
        for token in cluster.text.split(' '):
            if token in stop_words or token in designators:
                continue
            if token in morph:
                token = morph[token]
            if token in stop_words or token in designators:
                continue
            tokens.append(token)
        text = ' '.join(tokens) if tokens else cluster.text
        if text not in new_clusters:
            new_cluster = Cluster('NIL{:07d}'.format(len(new_clusters)), text)
            new_clusters[text] = new_cluster
        cluster_map.append((cluster, new_clusters[text]))
    for old_cluster, new_cluster in cluster_map:
        new_cluster.merge(old_cluster)
        for result in old_cluster.results:
            result_cluster_map[result] = new_cluster
    clusters = new_clusters
    logger.info('  # clusters: {} (Normalization)'.format(len(clusters)))

    # 2. NYSIIS
    new_clusters = {}
    cluster_map = []
    for _, cluster in clusters.items():
        text = cluster.text
        text_trim = re.sub(r'[ʼ’‘´′]', '\'', text) # normalize
        text_trim = re.sub(r'(.)\1+', r'\1', text_trim) # shorten double letters
        if len(text_trim) < 4:
            text_trim = text
        if text_trim not in new_clusters:
            new_cluster = Cluster('NIL{:07d}'.format(len(new_clusters)),
                                  text_trim)
            new_clusters[text_trim] = new_cluster
        cluster_map.append((cluster, new_clusters[text_trim]))
    for old_cluster, new_cluster in cluster_map:
        new_cluster.merge(old_cluster)
        for result in old_cluster.results:
            result_cluster_map[result] = new_cluster
    clusters = new_clusters
    logger.info('  # clusters: {} (NYSIIS)'.format(len(clusters)))

    # 3. Similar
    new_clusters = {}
    cluster_map = []
    for _, cluster in clusters.items():
        text = cluster.text
        similar = []
        if len(text) > 5:
            for new_cluster_text, new_cluster in new_clusters.items():
                distance = jellyfish.levenshtein_distance(text,
                                                          new_cluster_text)
                if distance < len(text) // 8 + 1:
                    similar.append((new_cluster_text, distance))
            similar = sorted(similar, key=lambda x : x[1])
        if similar:
            cluster_map.append((cluster, new_clusters[similar[0][0]]))
        else:
            new_cluster = Cluster('NIL{:07d}'.format(len(new_clusters)), text)
            new_clusters[text] = new_cluster
            cluster_map.append((cluster, new_clusters[text]))
    for old_cluster, new_cluster in cluster_map:
        new_cluster.merge(old_cluster)
        for result in old_cluster.results:
            result_cluster_map[result] = new_cluster
    clusters = new_clusters
    logger.info('  # clusters: {} (Similar)'.format(len(clusters)))

    # 4. Acronym

    # 5. Translation
    new_clusters = {}
    cluster_map = []
    translation_map = {}
    for _, cluster in clusters.items():
        translation_set = set()
        for result in cluster.results:
            for translation in result.translations:
                if translation:
                    translation_set.add(translation.lower())
        if len(translation_set) > 0:
            new_cluster = None
            for translation in translation_set:
                if translation in translation_map:
                    new_cluster = translation_map[translation]
                    break
            if new_cluster:
                new_cluster.merge(cluster)
                for translation in translation_set:
                    if translation not in translation_map:
                        translation_map[translation] = new_cluster
            else:
                new_cluster = Cluster('NIL{:07d}'.format(len(new_clusters)),
                                      cluster.text, cluster)
                new_clusters[cluster.text] = new_cluster
                for translation in translation_set:
                    translation_map[translation] = new_cluster
        else:
            new_cluster = Cluster('NIL{:07d}'.format(len(new_clusters)),
                                  cluster.text, cluster)
            new_clusters[cluster.text] = new_cluster
    clusters = new_clusters
    logger.info('  # clusters: {} (Translation)'.format(len(clusters)))

    # 6. Group
    new_clusters = {}
    if resources and 'group' in resources:
        # clean group
        all_mentions = set()
        for _, cluster in clusters.items():
            for result in cluster.results:
                all_mentions.add(result.text)
        groups = []
        for group in resources['group']:
            found = False
            for mention in group:
                if mention in all_mentions:
                    found = True
            if found:
                groups.append(group)
        for group in groups:
            new_cluster = Cluster('NIL{:07d}'.format(len(new_clusters)),
                                  group[0])
            new_clusters[group[0]] = new_cluster
        for _, cluster in clusters.items():
            text = cluster.text
            group_text = None
            for result in cluster.results:
                for group in res['group']:
                    if result.text in group:
                        group_text = group[0]
                        break
            if group_text and group_text in new_clusters:
                new_clusters[group_text].merge(cluster)
            elif text in new_clusters:
                new_clusters[text].merge(cluster)
            else:
                new_cluster = Cluster('NIL{:07d}'.format(len(new_clusters)),
                                      text)
                new_cluster.merge(cluster)
                new_clusters[text] = new_cluster
        # for old_cluster, new_cluster in cluster_map:
        #     new_cluster.merge(old_cluster)
        #     for result in old_cluster.results:
        #         result_cluster_map[result] = new_cluster
        clusters = new_clusters
        logger.info('  # clusters: {} (Group)'.format(len(clusters)))

    mention_cluster = {}
    for _, cluster in clusters.items():
        for result in cluster.results:
            if result.text not in mention_cluster:
                mention_cluster[result.text] = cluster.name

    # Assign NIL id
    nil_table = {}
    count = {
        'nilmention': 0,
        'nilid': 0
    }
    for docid in corpus:
        for em in corpus[docid]:
            if not em.entity:
                count['nilmention'] += 1
                nilid = mention_cluster[em.text]
                if nilid in nil_table:
                    nilentity = nil_table[nilid]
                else:
                    count['nilid'] += 1
                    nilentity = Entity(nilid)
                    nilentity.kbid2 = nilid
                    nilentity.confidence = 1.0
                    nil_table[nilid] = nilentity
                em.entity = nilentity
    logger.info('  # of NIL IDs: %s' % (count['nilid']))
    logger.info('  # of NIL mentions: %s' % (count['nilmention']))

    # Propagate kbid in the same cluster
    if propagate:
        logger.info('APPLYING CLUSTER PROPAGATION...')
        clusters = defaultdict(list)
        for docid in corpus:
            for em in corpus[docid]:
                cluster_id = mention_cluster[em.text]
                clusters[cluster_id].append(em)
        history = defaultdict(int)
        for clu in clusters:
            kbids = defaultdict(list)
            for em in clusters[clu]:
                kbids[em.entity.kbid].append(em)
            if len(kbids) > 1:
                kbid_clu = sorted(kbids,
                                  key=lambda x: len(kbids[x]), reverse=True)[0]
                if kbid_clu.startswith('NIL'):
                    continue
                for kbid in kbids:
                    if kbid == kbid_clu:
                        continue
                    if len(kbids[kbid_clu]) < len(kbids[kbid]):
                        continue
                    if not kbid.startswith('NIL'):
                        continue
                    for em in kbids[kbid]:
                        msg = '  %s | %s -> %s' % (em.text, em.entity.kbid,
                                                   kbids[kbid_clu][0].entity.kbid)
                        history[msg] += 1
                        em.entity = kbids[kbid_clu][0].entity
                        em.translations = kbids[kbid_clu][0].translations

        logger.info('  # of mention propagated: %s' % (len(history)))
        if verbose:
            for i in history:
                logger.info('%s | %s' % (i, history[i]))


def nil_clustering_exact_match(corpus):
    nil_table = {}
    count = {
        'nilmention': 0,
        'nilid': 0
    }
    for docid in corpus:
        for em in corpus[docid]:
            if not em.entity:
                count['nilmention'] += 1
                if em.text in nil_table:
                    nilentity = nil_table[em.text]
                else:
                    nilid = 'NIL' + \
                            '{number:0{width}d}'.format(width=7,
                                                        number=count['nilid'])
                    nilentity = Entity(nilid)
                    nilentity.confidence = 1.0
                    nil_table[em.text] = nilentity
                    count['nilid'] += 1
                em.entity = nilentity
    logger.info('  # of NIL IDs: %s' % (count['nilid']))
    logger.info('  # of NIL mentions: %s' % (count['nilmention']))
