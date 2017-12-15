class EntityMention(object):
    '''
    Entity Mention Class
    '''

    def __init__(self, text, beg=0, end=0, text_tok=None, docid=None,
                 context=None, vector=None, etype=None, entity=None,
                 candidates=None, translations=None, nominalmentions=None):
        self.text = text
        self.beg = int(beg)
        self.end = int(end)
        self.text_tok = text_tok or []
        self.docid = docid
        self.context = context or []
        self.vector = vector
        self.etype = etype
        self.entity = entity
        self.candidates = candidates or []
        self.translations = translations or []
        self.nominalmentions = nominalmentions or []

    def __str__(self):
        res = ''
        res += '%s\n' % (self.context)
        res += 'M: %s\n' % (self.text)
        if self.nominalmentions:
            res += 'N: %s\n' % ([i.text for i in self.nominalmentions])
        else:
            res += 'N: None\n'
        res += '%s\n' % (self.etype)
        if self.entity:
            res += 'E: %s\n' % (self.entity.kbid)
        else:
            res += 'E: None\n'
        for c in self.candidates:
            res += '   %s\n'  % str(c)
        return res

    def to_tac_tab_format(self, add_trans=False, kbid_format='kbid'):
        mention = self.text.replace('\t', ' ') \
                           .replace('\n', ' ') \
                           .replace('\r', ' ')
        offset = '%s:%s-%s' % (self.docid, self.beg, self.end)
        etype = self.etype
        mtype = 'NAM'
        if not self.entity:
            kbid = 'NIL'
            conf = '1.0'
        else:
            if kbid_format == 'all':
                kbid = '%s|%s|%s' % (self.entity.kbid,
                                     str(self.entity._kbid), self.entity.name)
            elif kbid_format == 'alternative':
                kbid = str(self.entity._kbid)
            else:
                kbid = self.entity.kbid
            conf = '{0:.16f}'.format(self.entity.confidence)
        if not add_trans:
            return [mention, offset, kbid, etype, mtype, conf]
        else:
            trans = '|'.join(self.translations)
            return [mention, offset, kbid, etype, mtype, conf, trans]


class NominalMention(object):
    '''
    Nominal Mention Class
    '''

    def __init__(self, text, beg=0, end=0, docid=None,
                 context=None, mtype=None, etype=None,
                 entitymention=None):
        self.text = text
        self.entitymention = entitymention
        self.beg = int(beg)
        self.end = int(end)
        self.docid = docid
        self.context = context
        self.mtype = mtype

    def to_tac_tab_format(self, add_trans=False, kbid_format='kbid'):
        mention = self.text.replace('\t', ' ') \
                           .replace('\n', ' ') \
                           .replace('\r', ' ')
        offset = '%s:%s-%s' % (self.docid, self.beg, self.end)
        etype = self.etype
        mtype = self.mtype
        if not self.entitymention.entity:
            kbid = 'NIL'
            conf = '1.0'
        else:
            if kbid_format == 'all':
                kbid = '%s|%s|%s' % (self.entitymention.entity.kbid,
                                     str(self.entitymention.entity._kbid),
                                     self.entitymention.entity.name)
            elif kbid_format == 'alternative':
                kbid = str(self.entitymention.entity._kbid)
            else:
                kbid = self.entitymention.entity.kbid
            conf = '{0:.16f}'.format(self.entitymention.entity.confidence)
        return [mention, offset, kbid, etype, mtype, str(conf)]


class Entity(object):
    '''
    Entity Class
    '''

    def __init__(self, kbid, name=None, etype=None, vector=None, features=None):
        self.kbid = kbid
        self._kbid = None
        self.name = name
        self.etype = etype
        self.vector = vector
        self.features = features or {}
        self.confidence = 1.0

    def __str__(self):
        res = '%s %s %s\n%s' % (self.kbid, self.etype, self.confidence,
                                self.features)
        return res
