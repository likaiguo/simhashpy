# coding:utf-8
'''
Created on 2015年9月24日

@author: likaiguo
'''
from __future__ import division, unicode_literals

from _collections import defaultdict
import collections
import datetime
import hashlib
import logging
import re
import sys
import time

from bs4 import BeautifulSoup
from fuzzywuzzy import fuzz

from utils.timer import Timer

from .simcache import SIMCACHE
from .simhash_model import SimHashCache, SimhashInvertedIndex


def add_dup_simhash_caches(simhashcache, dup_obj_ids):
    if not dup_obj_ids:
        return
    old_dup_obj_ids = set(dup_obj_ids)
    start_time = time.time()
    for i, dup_obj_id in enumerate(dup_obj_ids, 1):
        with Timer(msg='fuzzy-like:%d %s' % (i, dup_obj_id)):
            logging.info('--' * 100)
            try:
                dup_simhash = SimHashCache.objects.get(obj_id=dup_obj_id)
            except Exception, e:
                print e
                continue
            sim_ratio = fuzz.partial_ratio(s1=simhashcache.text, s2=dup_simhash.text)
            logging.info(simhashcache.text)
            logging.info('--' * 20)
            logging.info(dup_simhash.text)
            logging.info("%d %s %s" % (sim_ratio, simhashcache.obj_id, dup_simhash.obj_id))

            if dup_simhash not in old_dup_obj_ids:
                if sim_ratio > 50:
                    old_dup_obj_ids.add(dup_obj_id)
            else:
                if sim_ratio <= 50:
                    old_dup_obj_ids.remove(dup_obj_id)
    if dup_obj_ids or dup_obj_ids:
        simhashcache.dup_count = len(old_dup_obj_ids)
        simhashcache.dup_obj_ids = list(old_dup_obj_ids)
        simhashcache.save()
    print (time.time() - start_time) * 100


class Simhash(object):

    def __init__(self, value, f=64, reg=r'[\w\u4e00-\u9fcc]+', hashfunc=None):
        """
        `f` is the dimensions of fingerprints

        `reg` is meaningful only when `value` is basestring and describes
        what is considered to be a letter inside parsed string. Regexp
        object can also be specified (some attempt to handle any letters
        is to specify reg=re.compile(r'\w', re.UNICODE))

        `hashfunc` accepts a utf-8 encoded string and returns a unsigned
        integer in at least `f` bits.
        """

        self.f = f
        self.reg = reg
        self.value = None

        if hashfunc is None:
            def _hashfunc(x):
                # 一些缓存,这个值可以继续扩大
                if x in SIMCACHE:
                    return SIMCACHE[x]
                return int(hashlib.md5(x).hexdigest(), 16)

            self.hashfunc = _hashfunc
        else:
            self.hashfunc = hashfunc

        if isinstance(value, Simhash):
            self.value = value.value
        elif isinstance(value, basestring):
            self.build_by_text(unicode(value))
        elif isinstance(value, collections.Iterable):
            self.build_by_features(value)
        elif isinstance(value, long):
            self.value = value
        else:
            raise Exception('Bad parameter with type {}'.format(type(value)))

    def _slide(self, content, width=4):
        return [content[i:i + width] for i in range(max(len(content) - width + 1, 1))]

    def _tokenize(self, content):
        """
        分词
        """
        content = content.lower()
        content = ''.join(re.findall(self.reg, content))
        ans = self._slide(content)
        return ans

    def build_by_text(self, content):
        features = self._tokenize(content)
        return self.build_by_features(features)

    def build_by_features(self, features):
        hashs = [self.hashfunc(w.encode('utf-8')) for w in features]
        v = [0] * self.f
        masks = [1 << i for i in range(self.f)]
        for h in hashs:
            for i in range(self.f):
                v[i] += 1 if h & masks[i] else -1
        ans = 0
        for i in range(self.f):
            if v[i] >= 0:
                ans |= masks[i]
        self.value = ans

    def distance(self, another):
        """
        计算海明距离，海明距离在二进制中表现为 xor，数出1的个数
        """
        assert self.f == another.f
        x = (self.value ^ another.value) & ((1 << self.f) - 1)
        ans = 0
        while x:
            ans += 1
            x &= x - 1
        return ans


class SimhashIndex(object):

    def __init__(self, objs, f=64, k=2):
        """
        `objs` is a list of (obj_id, simhash)
        obj_id is a string, simhash is an instance of Simhash
        `f` is the same with the one for Simhash
        `k` is the tolerance
        """
        self.k = k
        self.f = f
        count = len(objs)
        logging.info('Initializing %s data.', count)
        # 最关键的点,全放在内存中的
        self.bucket = {}

        for i, q in enumerate(objs):
            if i % 10000 == 0 or i == count - 1:
                logging.info('%s/%s', i + 1, count)

            self.add(*q)

    def get_near_dups(self, simhash):
        """
        `simhash` is an instance of Simhash
        return a list of obj_id, which is in type of str
        """
        assert simhash.f == self.f

        ans = set()

        for key in self.get_keys(simhash):
            dups = self.bucket.get(key, set())
            logging.debug('key:%s', key)
            if len(dups) > 200:
                logging.warning('Big bucket found. key:%s, len:%s', key, len(dups))

            for dup in dups:
                sim2, obj_id = dup.split(',', 1)
                sim2 = Simhash(long(sim2, 16), self.f)

                d = simhash.distance(sim2)
                if d <= self.k:
                    ans.add(obj_id)
        return list(ans)

    def add(self, obj_id, simhash):
        """
        `obj_id` is a string
        `simhash` is an instance of Simhash
        #构建倒排索引
        """
        assert simhash.f == self.f

        for key in self.get_keys(simhash):
            v = '%x,%s' % (simhash.value, obj_id)

            self.bucket.setdefault(key, set())
            self.bucket[key].add(v)

    def delete(self, obj_id, simhash):
        """
        `obj_id` is a string
        `simhash` is an instance of Simhash
        """
        assert simhash.f == self.f

        for key in self.get_keys(simhash):
            v = '%x,%s' % (simhash.value, obj_id)

            if v in self.bucket.get(key, set()):
                self.bucket[key].remove(v)

    @property
    def offsets(self):
        """
        You may optimize this method according to <http://www.wwwconference.org/www2007/papers/paper215.pdf>
        #理解没有到位，预先设置的k值，对于生成倒排的分块非常重要
        """
        return [self.f // (self.k + 1) * i for i in range(self.k + 1)]

    def get_keys(self, simhash):
        """
        @summary: 将hash值分块,构建倒排索引的键
        #yield的作用非常值得学习
        """
        for i, offset in enumerate(self.offsets):
            m = (i == len(self.offsets) - 1 and 2 ** (self.f - offset) - 1 or 2 ** (self.offsets[i + 1] - offset) - 1)
            c = simhash.value >> offset & m
            yield '%x:%x' % (c, i)

    def bucket_size(self):
        return len(self.bucket)


class SimhashIndexWithMongo(object):

    def __init__(self, objs=(), f=64, k=2, hash_type='resume'):
        """
        `objs` is a list of (obj_id, origin_text)
         obj_id is a string, simhash is an instance of Simhash
        `f` is the same with the one for Simhash
        `k` is the tolerance 默认选择2的原因。 按照Charikar在论文中阐述的，64位simhash，
                            海明距离在3以内的文本都可以认为是近重复文本。
                            当然，具体数值需要结合具体业务以及经验值来确定。
         `hash_type` is the hash type  of the text

        #需要构建两个容器
        1.原始的文本数据以及hash后的hash值,和简单的更新时间等
        2.倒排索引的容器, 存储hash值进行离散后的  索引
        """
        self.k = k
        self.f = f
        self.hash_type = hash_type
        count = len(objs)
        logging.info('Initializing %s data.', count)

        for i, q in enumerate(objs):
            if i % 10000 == 0 or i == count - 1:
                logging.info('%s/%s', i + 1, count)
            self.add(*q)

    def insert(self, obj_id=None, value=None):
        """
        @summary: 插入一个hash值
        data can  be text,{obj_id,text},  {obj_id,simhash}
        #TODO:存储读写数据库最耗时的地方
        """
        assert value != None
        if isinstance(value, (str, unicode)):
            simhash = Simhash(value=value, f=self.f)
        elif isinstance(value, Simhash):
            simhash = value
        else:
            raise 'value not text or simhash'
        assert simhash.f == self.f
        # 缓存原始文本信息
        if obj_id and simhash:
            with Timer(msg='add_simhash_cache'):
                # 存储或者更新缓存
                simhashcaches = SimHashCache.objects.filter(obj_id=obj_id,
                         hash_type=self.hash_type).exclude('text').order_by('-update_time')
                if simhashcaches:
                    simhashcache = simhashcaches[0]
                else:
                    simhashcache = SimHashCache(obj_id=obj_id,
                                hash_type=self.hash_type)
                if isinstance(value, (str, unicode)):
                    simhashcache.text = value
                simhashcache.update_time = datetime.datetime.now()
                simhashcache.hash_value = "%x" % simhash.value
                simhashcache.save()
            with Timer(msg='add_invert_index'):
                # 存储倒排索引
                v = '%x,%s' % (simhash.value, obj_id)  # 转换成16进制,压缩,查询时候转回来,可以节省空间
                for key in self.get_keys(simhash):
                    with Timer(msg='add_invert_index-update_index-insert'):
                        try:
                            invert_index = SimhashInvertedIndex(key=key, hash_type=self.hash_type,
                                                            simhash_value_obj_id=v
                                                                )
                            invert_index.save()
                        except Exception, e:
                            print '%s,%s,%s' % (e, key, v)
                            pass

            return simhashcache

    def find(self, value, k=2, exclude_obj_ids=set(), exclude_obj_id_contain=None):
        """
        查找相似的text的 id,逻辑比较复杂
        1.分割要查找的origin_simhash的value成为多个key
        2.将每个key查询倒排索引,得到对应可能相似的 related_simhash
        3.求origin_simhash与 related_simhash之间的编辑距离 d

        4.统计每个related_simhash和对应 编辑距离 d
        5.多次出现的求一个额外的平均信息

        6.将related_simhash按照 d从小到大排序
        """
        assert value != None

        if isinstance(value, (str, unicode)):
            simhash = Simhash(value=value, f=self.f)
        elif isinstance(value, Simhash):
            simhash = value
        else:
            raise 'value not text or simhash'
        assert simhash.f == self.f
        sim_hash_dict = defaultdict(list)
        ans = set()
        for key in self.get_keys(simhash):
            with Timer(msg='==query: %s' % key):
                simhash_invertindex = SimhashInvertedIndex.objects.filter(key=key)
                if simhash_invertindex:
                    simhash_caches_index = [sim_index.simhash_value_obj_id
                                        for sim_index in simhash_invertindex]
                else:
    #                 logging.warning('SimhashInvertedIndex not exists key %s: %s' % (key, e))
                    continue
            with Timer(msg='find d < k %d' % (k)):
                if len(simhash_caches_index) > 200:
                    logging.warning('Big bucket found. key:%s, len:%s', key, len(simhash_caches_index))
                for simhash_cache in simhash_caches_index:
                    try:
                        sim2, obj_id = simhash_cache.split(',', 1)
                        if obj_id in exclude_obj_ids or \
                        (exclude_obj_id_contain and exclude_obj_id_contain in simhash_cache):
                            continue

                        sim2 = Simhash(long(sim2, 16), self.f)
                        d = simhash.distance(sim2)
    #                     print '**' * 50
    #                     print "d:%d obj_id:%s key:%s " % (d, obj_id, key)
                        sim_hash_dict[obj_id].append(d)
                        if d < k:
                            ans.add(obj_id)
                    except Exception, e:
                        logging.warning('not exists %s' % (e))
        return list(ans)

    @staticmethod
    def query_simhash_cache(obj_id):
        """
        @summary: 通过obj_id,查询相似的simhash对象
        """
        simhash_caches = SimHashCache.objects.filter(obj_id__contains=obj_id)

        return simhash_caches

    @staticmethod
    def find_similiar(obj_id):
        """

        """
        simhash_caches = SimHashCache.objects.filter(obj_id__contains=obj_id)
        return simhash_caches

    def delete(self, obj_id, simhash):
        """
        `obj_id` is a string
        `simhash` is an instance of Simhash
        """
        assert simhash.f == self.f
        try:
            simhashcache = SimHashCache.objects.get(obj_id=obj_id, hash_type=self.hash_type)
        except Exception, e:
            logging.warning('not exists %s' % (e))
            return

        for key in self.get_keys(simhash):
            try:
                simhash_invertindex = SimhashInvertedIndex.objects.get(key=key)
                if simhashcache in simhash_invertindex.simhash_caches_index:
                    simhash_invertindex.simhash_caches_index.remove(simhashcache)
                    simhash_invertindex.save()
            except Exception, e:
                logging.warning('not exists %s' % (e))

    def add(self, obj_id, simhash):
        """
        `obj_id` is a string
        `simhash` is an instance of Simhash
        #
        1.构建原始文本的hash的值后
        2.构建倒排索引
        """
        return self.insert(obj_id=obj_id, value=simhash)

    def add_and_find_dup(self, obj_id, value, k=16):
        """
        添加一个键值对文档,并且找到最相似的文档并且写入 simhashcache中,
        目的: 为了在建立的过程中尽量找到相关连的simhash.

        实际上在一个大规模的文档排重的过程中,后边总会有一部分的文档与前边相似
        为了避免再次重复读入,所以构建该子段
        """
        simhash = BeautifulSoup(value, "lxml").get_text('\n')
        simhashcache = self.add(obj_id=obj_id, simhash=simhash)
        with Timer(msg='find'):
            dup_obj_ids = self.find(value=simhash, k=k, exclude_obj_id_contain=obj_id.split('_')[0])
        if dup_obj_ids:
            with Timer(msg='add_dup_simhash_caches'):
                add_dup_simhash_caches(simhashcache, dup_obj_ids)

        return simhashcache

    def get_near_dups(self, simhash):
        """
        `simhash` is an instance of Simhash
        return a list of obj_id, which is in type of str
        """
        return self.find(simhash, self.k)

    @property
    def offsets(self):
        """
        You may optimize this method according to <http://www.wwwconference.org/www2007/papers/paper215.pdf>
        """
        return [self.f // (self.k + 1) * i for i in range(self.k + 1)]

    def get_keys(self, simhash):
        """
        @summary: 将hash值分块,构建倒排索引的键
        #yield的作用非常值得学习
        """
        for i, offset in enumerate(self.offsets):
            m = (i == len(self.offsets) - 1 and 2 ** (self.f - offset) - 1 or 2 ** (self.offsets[i + 1] - offset) - 1)
            c = simhash.value >> offset & m
            yield '%x:%x' % (c, i)

    def bucket_size(self):
        return SimhashInvertedIndex.objects.count()
