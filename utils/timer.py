# coding:utf-8
"""
Created on 2015年8月20日

@author: likaiguo & chenruotian
Python 性能分析入门指南
http://segmentfault.com/a/1190000000616798
"""
import time
from utils.logger import clogger, Logger


class Timer(object):
    """时间计算器

     time_grain: 时间粒度 - 秒s/毫秒ms， 默认毫秒ms
     verbose_in: 进入Timer时是否输出msg_in
     verbose_out: 退出Timer时是否输出msg_out
     verbose: 退出Timer时是否输出msg
     msg_in: 进入Timer时需要输出的消息，不为空时才真正输出
     msg_out: 退出Timer时需要输出的消息，不为空时才真正输出
     msg: 退出Timer时需要输出的消息，和计时结果一起输出，不为空时才真正输出
    """

    def __init__(self, time_grain=u'ms',
                 verbose_in=True, verbose_out=True, verbose=True,
                 msg_in=u'', msg_out=u'', msg=u'', logfile=None):
        self.time_grain = time_grain
        self.verbose_in = verbose_in
        self.verbose_out = verbose_out
        self.verbose = verbose
        self.msg_in = msg_in
        self.msg_out = msg_out
        self.msg = msg
        if logfile:
            self.logger = Logger('flogger', log2console=False, log2file=True,
                                 logfile=logfile).get_logger()
        else:
            self.logger = clogger

    def __enter__(self):
        if self.verbose_in and self.msg_in:
            self.logger.info('%s' % self.msg_in)
        self.start = time.time()

    def __exit__(self, *args):
        self.end = time.time()

        self.secs = self.end - self.start  # secs
        self.msecs = self.secs * 1000  # millisecs
        tm_str = ('%fs' % self.secs) if self.time_grain == u's' else (
            '%.3fms' % self.msecs)

        if self.verbose_out and self.msg_out:
            self.logger.info('%s' % self.msg_out)

        if self.verbose:
            if self.msg:
                self.logger.info('elapsed: %s, %s' % (tm_str, self.msg))
            else:
                self.logger.info('elapsed: %s' % tm_str)

if __name__ == '__main__':
    with Timer(msg_in=u'start test ...',
               msg_out=u'complete test',
               msg=u'test'
               ):
        from time import sleep
        sleep(1)
        print '1'
        sleep(1)
        print(2)

    # def primes(n):
    #     if n == 2:
    #         return [2]
    #     elif n < 2:
    #         return []
    #     s = range(3, n + 1, 2)
    #     mroot = n ** 0.5
    #     half = (n + 1) / 2 - 1
    #     i = 0
    #     m = 3
    #     while m <= mroot:
    #         if s[i]:
    #             j = (m * m - 3) / 2
    #             s[j] = 0
    #             while j < half:
    #                 s[j] = 0
    #                 j += m
    #         print m
    #         i = i + 1
    #         m = 2 * i + 3
    #     return [2] + [x for x in s if x]
    # print primes(100)
