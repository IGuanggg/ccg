from ccb_common import CcbCommon
import requests
import json
from json import JSONEncoder
from collections import namedtuple
import time
import urllib
from urllib.parse import urlparse
from urllib import parse
import os
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

# 瓜分十亿积分
shortId_gfsyjf = 'oDtOaEyJuCD8d8XGii5KnA'

class CcbGfsyjf:

    #活动结束日期
    stop_time = '2022-11-30'
    ccbCommon = None

    #抽卡次数
    drawCount = 0
    runStatus = True
    log = ''

    def __init__(self, ccbCommon):
        self.ccbCommon = ccbCommon

    def exec(self):
        #瓜分十亿积分
        try:
            currentTime = datetime.now().strftime('%Y-%m-%d')
            if(currentTime > self.stop_time):
                self.runStatus = False
                self.log = '活动已结束，积分结算发放时间：2022年12月1日-2022年12月20日'   
                return
            shareCode = self.ccbCommon.getShareData('gfsyjf')
            redirectResult = self.ccbCommon.requestToken(shortId_gfsyjf, '6000100',u=shareCode)
            redirectUrl = redirectResult['redirectUrl']
            redirectCookie = redirectResult['cookie']
            # logger.info(f"redirectUrl：{redirectUrl}")
            gfsyjfResult = self.ccbCommon.captureWebCK(redirectUrl, redirectCookie, '抓取瓜分十亿积分参数') # home_domain, yldk_domain,
            gfsyjf_cookie = gfsyjfResult['cookie']
            gfsyjf_url = gfsyjfResult['url']
            gfsyjf_domain = gfsyjf_url[0:gfsyjf_url.find('/',gfsyjf_url.find('://')+3)]
            gfsyjf_csrfToken = gfsyjfResult['csrfToken']
            self.getShareCode(gfsyjf_domain ,gfsyjf_cookie)
            self.gfsyjfGetIndex(gfsyjf_domain, gfsyjf_cookie, gfsyjf_csrfToken, True)
            if(self.runStatus):
                self.gfsyjfGetIndex(gfsyjf_domain, gfsyjf_cookie, gfsyjf_csrfToken, False)
        except Exception as e:
            self.runStatus = False
            logger.error('出错了！', e)


    # 瓜分十亿积分 - 查询抽卡次数
    def gfsyjfGetIndex(self, gfsyjf_domain, cookie, csrfToken, drawFlag):
        url_gfsyjf_index = f'{gfsyjf_domain}/activity/dmspjkpgfjf/userinfo/224/5P87EL3y'
        title = '瓜分十亿积分-查询抽卡次数'
        logger.info(f"\n开始{title}")
        url = url_gfsyjf_index
        headers = {'content-type': "application/json", 'User-Agent':User_Agent, 'X-CSRF-TOKEN':csrfToken}
        resp = requests.get(url,  headers = headers, cookies=cookie)
        if resp.status_code >= 200 and resp.status_code < 300:
            content = resp.content.decode('utf-8')
            result = json.loads(content, object_hook=customStudentDecoder)
            if(result.status=='success'):
                if(drawFlag):
                    remainNum = int(result.data.remain)
                    logger.info(f'共有{remainNum}次抽卡的机会')
                    for i in range(0,remainNum):
                        self.gfsyjfDrawPrize(gfsyjf_domain, cookie, csrfToken)
                        logger.info('延时5秒')
                        time.sleep(5)    
                else:
                    card = json.loads(content).get('data').get('cards')
                    shi =  card.get('shi', 0)
                    yi =   card.get('yi', 0)
                    jian = card.get('jian', 0)
                    hang = card.get('hang', 0)
                    ji =   card.get('ji', 0)
                    fen =  card.get('fen',0)
                    self.log = f'十[{shi}]、亿[{yi}]、建[{jian}]、行[{hang}]、积[{ji}]、分[{fen}]'
            else:
                logger.info(f'{title}接口返回错误！')
                logger.info(result)
        else:
            logger.info(f'{title}接口调用失败！{resp.status_code}')
            logger.info(resp.content)

    # 瓜分十亿积分 - 抽卡
    def gfsyjfDrawPrize(self, gfsyjf_domain, cookie, csrfToken):
        url_gfsyjf_drawPrize=f'{gfsyjf_domain}/activity/dmspjkpgfjf/draw/224/5P87EL3y'
        title = '瓜分十亿积分抽卡'
        logger.info(f"\n开始{title}")
        url = url_gfsyjf_drawPrize
        headers = {'content-type': "application/json", 'User-Agent':User_Agent, 'X-CSRF-TOKEN':csrfToken}
        resp = requests.post(url, data='{}', headers = headers, cookies=cookie)
        if resp.status_code >= 200 and resp.status_code < 300:
            self.drawCount+=1
            content = resp.content.decode('utf-8')
            result = json.loads(content, object_hook=customStudentDecoder)
            if(result.status=='success'):
                logger.info(f"{result.message} , {result.data}")
            else:
                logger.info(f'{title}接口返回错误！')
                logger.info(result)
                if(result.status=='fail' and result.message.find('未报名')>-1):
                    self.runStatus = False
                    self.log=f'{result.message} , 活动地址: https://syx3.dmsp.ccb.com/a/224/5P87EL3y/index '
        else:
            logger.info(f'{title}接口调用失败！{resp.status_code}')
            logger.info(resp.content)

    # 获取瓜分十亿积分助力码
    def getShareCode(self, gfsyjf_domain, cookie):
        url_gfsyjf_userInfo=f'{gfsyjf_domain}/Common/activity/getUserInfo/224/5P87EL3y'
        title = '获取瓜分十亿积分助力码'
        logger.info(f"\n开始{title}")
        url = url_gfsyjf_userInfo
        headers = {'User-Agent':User_Agent}
        resp = requests.get(url, headers = headers, cookies=cookie)
        if resp.status_code >= 200 and resp.status_code < 300:
            content = resp.content.decode('utf-8')
            result = json.loads(content, object_hook=customStudentDecoder)
            if(result.status=='success'):
                shareCode = result.data.ident
                logger.info(f'助力码：{shareCode}')
                self.ccbCommon.cacheShareData(shareCode, 'gfsyjf')
            else:
                logger.info(f'{title}接口返回错误！')
                logger.info(result)
        else:
            logger.info(f'{title}接口调用失败！{resp.status_code}')
            logger.info(resp.content)

