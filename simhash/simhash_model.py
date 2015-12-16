# coding:utf-8
'''
Created on 2015年8月13日

@author: likaiguo

不用list存储倒排索引,用单一键
'''
import datetime
import json


from mongoengine import Document, IntField
from mongoengine import StringField, ListField, DateTimeField
from mongoengine import register_connection
from config import simhash_mongodb_config
register_connection(**simhash_mongodb_config)

print 'simhash db\n', json.dumps(simhash_mongodb_config, indent=4)


class SimHashCache(Document):
    obj_id = StringField()
    hash_value = StringField()  # OverflowError: MongoDB can only handle up to 8-byte ints
    text = StringField()
    hash_type = StringField()  # 对应不同类型的hash来源,如:简历,职位描述
    dup_obj_ids = ListField(StringField())
    dup_count = IntField(default=0)
    add_time = DateTimeField(default=datetime.datetime.now())
    update_time = DateTimeField(default=datetime.datetime.now())

    meta = {
        'db_alias': 'simhash',
        'strict': False,
        "collection": "simhash-1",
        "indexes": [
            "-update_time",
            "-add_time",
            "obj_id",
            "hash_type",
            "-dup_count",
            {
                "fields": ["obj_id", "hash_type"],
                "unique":True,
            },
        ],

    }

    def __unicode__(self):

        return 'obj_id:%s' % (self.obj_id)

    def get_all_dup_ids(self):

        return [dup for dup in self.dup_obj_ids]


class SimhashInvertedIndex(Document):
    """
    simhash倒排索引
    """
    key = StringField()
#     simhash_caches_index = ListField(StringField())  # 倒排相似hash索引 hash_value,obj_id
    simhash_value_obj_id = StringField()  # hash索引 hash_value,obj_id
    hash_type = StringField()  # 对应不同类型的hash来源,如:简历,职位描述
    meta = {
        'db_alias': 'simhash',
        'strict': False,
#             'index_background': True ,
        "collection": "simhash_invert_index-2",
        "indexes": [
            "key",
            "simhash_value_obj_id",
            "hash_type",
            {
                    "fields": ["key", 'simhash_value_obj_id'],
                    "unique":True,
            },
        ]
    }


if __name__ == '__main__':
    from bson import ObjectId
    simhashcache3 = SimHashCache.objects.get(id=ObjectId("55ccdb40452f7159b9112543"))
    simhashcache3 = SimHashCache.objects.get(id=ObjectId("55cccc20452f714a0fbd8402"))
    simhashcache3 = SimHashCache.objects.get(id=ObjectId("55cce99a452f71684791a8b0"))
    simhashcache3 = SimHashCache.objects.get(id=ObjectId("55cd2965452f716b1ffe828d"))
    simhashcache3.add_dup_simhash_caches(simhashcache3.dup_simhashcache)
    simhashcache = SimHashCache(obj_id='123')
    simhashcache2 = SimHashCache(obj_id='456')
    simhashcache.save()
    simhashcache2.save()
    simhashcache.dup_simhashcache = [simhashcache2]
    simhashcache.save()
