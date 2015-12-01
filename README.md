# simhashpy
使用simhash算法,快速索引和查询大量文本

输入: 文本
输出: 重复文本及其id

##职位描述数据
数据为mongo导出的bson格式,  http://pan.baidu.com/s/1hqwHEBy 密码: im5v


##依赖包安装:
```
wget https://bootstrap.pypa.io/get-pip.py
python get_pip.py
pip install -r requirements.txt
```

###目录介绍
```
.
├── config  配置文件
├── data  数据模型
├── docs  文档
├── simhash
└── tests 单元测试,功能测试
```