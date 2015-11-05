# coding:utf-8
'''
Created on 2015年11月5日

@author: likaiguo
'''
from mongoengine import (Document,
                         StringField,
                         )
from mongoengine import register_connection
from config import mongodb_config
register_connection(**mongodb_config)


class Feed(Document):
    """
    @summary: 职位描述
    """

    keywords = StringField(default='')
    job_type = StringField(default='')  # 工作类型
    talent_level = StringField(default='')  # 人才级别
    expect_area = StringField(default='')  # 期望工作地
    job_desc = StringField(default='')  # 职位描述
    job_url = StringField(default='')


if __name__ == '__main__':
    feed = Feed.objects.first()
    print(feed)
