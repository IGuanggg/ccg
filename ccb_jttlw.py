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
import random

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

#街头投篮王
shortId_jttlw='jBzIB7blLdyF4l_vmNNOPg'

class CcbJttlw:

    ccbCommon = None

    #游戏次数
    runCount = 0
    #游戏赢得cc豆
    runGot=0
    #游戏门票
    ticket=15
    runStatus = True
 

    def __init__(self, ccbCommon):
        self.ccbCommon = ccbCommon

    def exec(self):
        # 街头投篮王
        try:
            redirectResult = self.ccbCommon.requestToken(shortId_jttlw, '6000111')
            redirectUrl = redirectResult['redirectUrl']
            redirectCookie = redirectResult['cookie']
            jttlwResult = self.ccbCommon.captureWebCK(redirectUrl, redirectCookie, '抓取街头投篮王参数')
            jttlw_cookie = jttlwResult['cookie']
            jttlw_url = jttlwResult['url']
            jttlw_domain = jttlw_url[0:jttlw_url.find('/',jttlw_url.find('://')+3)]
            jttlw_csrfToken = jttlwResult['csrfToken']
            self.jttlwInfo(jttlw_domain, jttlw_cookie, jttlw_csrfToken)
        except Exception as e:
            self.runStatus = False
            logger.error('出错了！', e)


    #街头投篮王 - 查询游戏次数
    def jttlwInfo(self, jttlw_domain, cookie, csrfToken):
        url_jttlw_userExtInfo=f'{jttlw_domain}/activity/dmspdunk/user/224/kZMpj7mW'
        title = '查询街头投篮王游戏次数'
        logger.info(f"\n开始{title}")
        url = url_jttlw_userExtInfo
        headers = {'User-Agent':User_Agent}
        resp = requests.get(url, headers = headers, cookies=cookie)
        if resp.status_code >= 200 and resp.status_code < 300:
            content = resp.content.decode('utf-8')
            result = json.loads(content, object_hook=customStudentDecoder)
            #logger.info(result)
            if(result.status=='success'):
                remainNum = int(result.data.remain_daily_times)
                tlCount = self.ccbCommon.tlCount if remainNum>self.ccbCommon.tlCount else remainNum
                logger.info(f'今日剩余游戏次数：{remainNum}, 玩{tlCount}次。')
                if(tlCount>0):
                    for i in range(0,tlCount):
                        self.jttlwDraw(jttlw_domain, cookie, csrfToken)
                        logger.info('延时5秒')
                        time.sleep(5)
                else:
                    logger.info("游戏次数已用完或已达到限定次数，结束！")
            else:
                logger.info(f'{title}接口返回错误！')
                logger.info(result)
        else:
            logger.info(f'{title}接口调用失败！{resp.status_code}')
            logger.info(resp.content)

    #街头投篮王 - 启动游戏
    def jttlwDraw(self, jttlw_domain, cookie, csrfToken):
        url_jttlw_draw=f'{jttlw_domain}/activity/dmspdunk/start/224/kZMpj7mW'
        title = '启动游戏'
        logger.info(f"\n开始{title}")
        url = url_jttlw_draw
        headers = {'content-type': "application/json", 'User-Agent':User_Agent, 'X-CSRF-TOKEN':csrfToken}
        resp = requests.post(url, headers = headers, cookies=cookie)
        if resp.status_code >= 200 and resp.status_code < 300:
            self.runCount+=1
            content = resp.content.decode('utf-8')
            result = json.loads(content, object_hook=customStudentDecoder)
            #logger.info(result)
            if(result.status=='success'):
                gameID=result.data.id
                self.jttlwGameInfo(jttlw_domain, cookie, csrfToken, gameID)
            else:
                logger.info(f'{title}接口返回错误！')
                logger.info(result)
        else:
            logger.info(f'{title}接口调用失败！{resp.status_code}')
            logger.info(resp.content)

    #街头投篮王 - 查询游戏分数
    def jttlwGameInfo(self, jttlw_domain, cookie, csrfToken, gameID):
        url_jttlw_game_info=f'{jttlw_domain}/activity/dmspdunk/scene/224/kZMpj7mW?id={gameID}'
        title = '查询街头投篮王游戏分数'
        logger.info(f"\n开始{title}")
        url = url_jttlw_game_info
        headers = {'User-Agent':User_Agent}
        resp = requests.get(url, headers = headers, cookies=cookie)
        if resp.status_code >= 200 and resp.status_code < 300:
            content = resp.content.decode('utf-8')
            result = json.loads(content, object_hook=customStudentDecoder)
            #logger.info(result)
            if(result.status=='success'):
                logger.info(f'剩余投篮：{result.data.remain_times}次， 限时：{result.data.valid_time}秒')                
                remainTimes = int(result.data.remain_times)
                validTime = int(result.data.valid_time)
                if(remainTimes>0 and validTime>0):
                    self.jttlwShoot(jttlw_domain, cookie, csrfToken, gameID)
            else:
                logger.info(f'{title}接口返回错误！')
                logger.info(result)
        else:
            logger.info(f'{title}接口调用失败！{resp.status_code}')
            logger.info(resp.content)

    #街头投篮王 - 投篮
    def jttlwShoot(self, jttlw_domain, cookie, csrfToken, gameID):
        delay = 2 
        logger.info(f'延时{delay}秒')
        time.sleep(delay)
        url_jttlw_shoot=f'{jttlw_domain}/activity/dmspdunk/shot/224/kZMpj7mW'
        title = '投篮'
        logger.info(f"\n开始{title}")
        url = url_jttlw_shoot
        payload = {'id':gameID}
        headers = {'content-type': "application/json", 'User-Agent':User_Agent, 'X-CSRF-TOKEN':csrfToken}
        resp = requests.post(url, data = json.dumps(payload), headers = headers, cookies=cookie)
        if resp.status_code >= 200 and resp.status_code < 300:
            content = resp.content.decode('utf-8')
            result = json.loads(content, object_hook=customStudentDecoder)
            #logger.info(result)
            if(result.status=='success'):
                gotCCB = int(result.data.got_ccb)
                remainTimes = int(result.data.remain_times)
                winTimes = int(result.data.win_times)
                validTime = int(result.data.valid_time)
                logger.info(f'游戏赢{gotCCB}CCB,剩余投篮{remainTimes}次,命中{winTimes}次,剩余时间{validTime}秒')
                if(remainTimes>0 and validTime>0):
                    self.jttlwShoot(jttlw_domain, cookie, csrfToken, gameID)
                else:
                    self.runGot = self.runGot + gotCCB
                    logger.info(f'游戏结束，共收获{gotCCB}CCB。')
            else:
                logger.info(f'{title}接口返回错误！')
                logger.info(result)
        else:
            logger.info(f'{title}接口调用失败！{resp.status_code}')
            logger.info(resp.content)