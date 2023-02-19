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

# 养老模块（早起打卡5点~9点）
shortId_yl = 'gsuZITMAkM-D6aNvsjxEKA'

class CcbYldk:

    ccbCommon = None

    #执行状态  True ： 打卡成功， Flase：打卡失败， None : 异常
    runStatus = False

    def __init__(self, ccbCommon):
        self.ccbCommon = ccbCommon

    def exec(self):
        #养老模块
        try:
            shareCode = self.ccbCommon.getShareData('yldk')
            redirectResult = self.ccbCommon.requestToken(shortId_yl, '6000111', u=shareCode)
            redirectUrl = redirectResult['redirectUrl']
            redirectCookie = redirectResult['cookie']
            # logger.info(f"养老模块redirectUrl：{redirectUrl}")
            yldkResult = self.ccbCommon.captureWebCK(redirectUrl, redirectCookie, '抓取养老打卡签到参数') # home_domain, yldk_domain,
            yldk_cookie = yldkResult['cookie']
            yldk_url = yldkResult['url']
            yldk_domain = yldk_url[0:yldk_url.find('/',yldk_url.find('://')+3)]
            self.getShareCode(yldk_domain ,yldk_cookie)
            self.yldkInfo(yldk_domain ,yldk_cookie)
        except Exception as e:
            self.runStatus = None
            logger.error('出错了！', e)

    #获取养老打卡-活动详情
    def yldkInfo(self, yldk_domain, cookie):
        url_yldk_info=f'{yldk_domain}/activity/dmsppension/index/224/lPYnXrmN'
        title = '获取养老打卡活动详情'
        logger.info(f"\n开始{title}")
        url = url_yldk_info
        headers = {'User-Agent':User_Agent}
        resp = requests.get(url, headers = headers, cookies=cookie)
        if resp.status_code >= 200 and resp.status_code < 300:
            content = resp.content.decode('utf-8')
            result = json.loads(content, object_hook=customStudentDecoder)
            if(result.status=='success'):            
                sceneList = result.data.scene_list
                nowDate = datetime.now()
                for scene in sceneList:
                    stime = datetime.strptime(scene.start_time, '%Y-%m-%d %H:%M:%S')
                    etime = datetime.strptime(scene.end_time, '%Y-%m-%d %H:%M:%S')
                    if(stime<=nowDate and nowDate <=etime):
                        logger.info(f"本期签到情况 {scene.start_time} ~ {scene.end_time}：")
                        currentStatus = None
                        for status in scene.sign_status:
                            logger.info(f'{status.date} status:{status.is_sign} {"已签到" if status.is_sign=="1" else "未签到"}')
                            tempDate = datetime.strptime(status.date, '%Y%m%d')
                            if(tempDate.year == nowDate.year and tempDate.month == nowDate.month and tempDate.day == nowDate.day and status.is_sign=="3"):
                                currentStatus = status
                        if(currentStatus!=None):
                            self.yldkSign(yldk_domain, cookie)
                        else:
                            self.runStatus = True
                            logger.info(f'今天【{nowDate}】已签到了，跳过签到！')
                        break
                # logger.info(result)
            else:
                logger.info(f'{title}接口返回错误！')
                logger.info(result)
        else:
            logger.info(f'{title}接口调用失败！{resp.status_code}')
            logger.info(resp.content)


    # 养老打卡-签到
    def yldkSign(self, yldk_domain, cookie):
        url_yldk_sign=f'{yldk_domain}/activity/dmsppension/sign/224/lPYnXrmN'
        title = '养老打卡签到'
        logger.info(f"\n开始{title}")
        url = url_yldk_sign
        headers = {'User-Agent':User_Agent}
        resp = requests.get(url, headers = headers, cookies=cookie)
        if resp.status_code >= 200 and resp.status_code < 300:
            content = resp.content.decode('utf-8')
            #logger.info(urllib.parse.unquote(content))
            self.runStatus = True
        else:
            logger.info(f'{title}接口调用失败！{resp.status_code}')
            logger.info(resp.content)

    # 获取养老打卡助力码
    def getShareCode(self, yldk_domain, cookie):
        url_yldk_userInfo=f'{yldk_domain}/Common/activity/getUserInfo/224/lPYnXrmN'
        title = '获取养老打卡助力码'
        logger.info(f"\n开始{title}")
        url = url_yldk_userInfo
        headers = {'User-Agent':User_Agent}
        resp = requests.get(url, headers = headers, cookies=cookie)
        if resp.status_code >= 200 and resp.status_code < 300:
            content = resp.content.decode('utf-8')
            result = json.loads(content, object_hook=customStudentDecoder)
            if(result.status=='success'):
                shareCode = result.data.ident
                logger.info(f'助力码：{shareCode}')
                self.ccbCommon.cacheShareData(shareCode, 'yldk')
            else:
                logger.info(f'{title}接口返回错误！')
                logger.info(result)
        else:
            logger.info(f'{title}接口调用失败！{resp.status_code}')
            logger.info(resp.content)

