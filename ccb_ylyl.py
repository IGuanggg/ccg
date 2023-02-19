from ccb_common import CcbCommon
import requests
import json
from json import JSONEncoder
from collections import namedtuple
import time
import urllib
from urllib.parse import urlparse
import os
import datetime
from datetime import datetime,timedelta
import logging
import logging.handlers
import traceback
# Shelve是对象持久化保存方法
from shelveHelper import ShelveHelp
from question import QuestionManager

# 日志模块
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logFormat = logging.Formatter("%(message)s")

# 日志输出流
stream = logging.StreamHandler()
stream.setFormatter(logFormat)
logger.addHandler(stream)

# 第三方库
try:
    import requests
except ModuleNotFoundError:
    logger.info("缺少requests依赖！程序将尝试安装依赖！")
    os.system("pip3 install requests -i https://pypi.tuna.tsinghua.edu.cn/simple")
    os.execl(sys.executable, 'python3', __file__, *sys.argv)

User_Agent = 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.138 Safari/537.36 NetType/WIFI MicroMessenger/7.0.20.1781(0x6700143B) WindowsWechat(0x6307062c)'
headers = {'content-type': "application/json", 'User-Agent':User_Agent}

def customStudentDecoder(studentDict):
    return namedtuple('X', studentDict.keys())(*studentDict.values())

#裕乐有礼
shortId_ylyl='pb31G1uCydhBkt4MRV9GGg'

class CcbYlyl:

    ccbCommon = None

    #刮卡次数
    runCount = 0
    runStatus = True

    def __init__(self, ccbCommon):
        self.ccbCommon = ccbCommon

    def exec(self):
        # 裕乐有礼
        try:
            redirectResult = self.ccbCommon.requestToken(shortId_ylyl, '6000111')
            redirectUrl = redirectResult['redirectUrl']
            redirectCookie = redirectResult['cookie']
            ylylResult = self.ccbCommon.captureWebCK(redirectUrl, redirectCookie, '抓取裕乐有礼参数')
            ylyl_cookie = ylylResult['cookie']
            ylyl_url = ylylResult['url']
            ylyl_domain = ylyl_url[0:ylyl_url.find('/',ylyl_url.find('://')+3)]
            ylyl_csrfToken = ylylResult['csrfToken']
            self.ylylInfo(ylyl_domain, ylyl_cookie, ylyl_csrfToken)
        except Exception as e:
            self.runStatus = False
            logger.error('出错了！', e)


    #裕乐有礼 - 查询刮卡次数
    def ylylInfo(self, ylyl_domain, cookie, csrfToken):
        url_ylyl_userExtInfo=f'{ylyl_domain}/Component/draw/getUserExtInfo/224/j3QLD5Zw'
        title = '查询裕乐有礼刮卡次数'
        logger.info(f"\n开始{title}")
        url = url_ylyl_userExtInfo
        headers = {'User-Agent':User_Agent}
        resp = requests.get(url, headers = headers, cookies=cookie)
        if resp.status_code >= 200 and resp.status_code < 300:
            content = resp.content.decode('utf-8')
            result = json.loads(content, object_hook=customStudentDecoder)
            # logger.info(result)
            if(result.status=='success'):
                remainNum = int(result.data.remain_num)
                logger.info(f'今日可刮卡次数：{remainNum}')
                # 这个地方不是今日剩余刮卡次数
                if(remainNum>0):
                    for i in range(0,remainNum):
                        self.ylylDraw(ylyl_domain, cookie, csrfToken)
                        logger.info('延时5秒')
                        time.sleep(5)
                else:
                    logger.info("刮卡次数已用完，跳过刮卡！")
            else:
                logger.info(f'{title}接口返回错误！')
                logger.info(result)
        else:
            logger.info(f'{title}接口调用失败！{resp.status_code}')
            logger.info(resp.content)

    #裕乐有礼 - 刮卡
    def ylylDraw(self, ylyl_domain, cookie, csrfToken):
        url_ylyl_draw=f'{ylyl_domain}/Component/draw/commonDrawPrize/224/j3QLD5Zw'
        title = '刮卡'
        logger.info(f"\n开始{title}")
        url = url_ylyl_draw
        logger.info(url)
        headers = {'content-type': "application/json", 'User-Agent':User_Agent, 'X-CSRF-TOKEN':csrfToken}
        resp = requests.post(url, headers = headers, cookies=cookie)
        if resp.status_code >= 200 and resp.status_code < 300:
            self.runCount+=1
            content = resp.content.decode('utf-8')
            result = json.loads(content, object_hook=customStudentDecoder)
            # logger.info(result)
            if(result.status=='success'):
                logger.info(f'{result.message}, {result.data.prizename}')
            else:
                logger.info(f'{title}接口返回错误！')
                logger.info(result)
        else:
            logger.info(f'{title}接口调用失败！{resp.status_code}')
            logger.info(resp.content)