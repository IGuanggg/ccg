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

# 丰收节
shortId_fsj = 'oDtOaEyJuCD8d8XGii5KnA'

class CcbFsj:

    ccbCommon = None

    #掷骰子次数
    drawCount = 0
    runStatus = True

    def __init__(self, ccbCommon):
        self.ccbCommon = ccbCommon

    def exec(self):
        #丰收节
        try:
            shareCode = self.ccbCommon.getShareData('fsj')
            redirectResult = self.ccbCommon.requestToken(shortId_fsj, '6000100',u=shareCode)
            redirectUrl = redirectResult['redirectUrl']
            redirectCookie = redirectResult['cookie']
            # logger.info(f"redirectUrl：{redirectUrl}")
            fsjResult = self.ccbCommon.captureWebCK(redirectUrl, redirectCookie, '抓取丰收节参数') # home_domain, yldk_domain,
            fsj_cookie = fsjResult['cookie']
            fsj_url = fsjResult['url']
            fsj_domain = fsj_url[0:fsj_url.find('/',fsj_url.find('://')+3)]
            fsj_csrfToken = fsjResult['csrfToken']
            self.fsjTask(fsj_domain ,fsj_cookie, fsj_csrfToken,0)
            self.getShareCode(fsj_domain ,fsj_cookie)
            self.fsjGetIndex(fsj_domain, fsj_cookie, fsj_csrfToken)
        except Exception as e:
            self.runStatus = False
            logger.error('出错了！', e)

    #获取丰收节-任务列表
    def fsjTask(self, fsj_domain, cookie, csrfToken, taskIndex):
        url_fsj_taskList=f'{fsj_domain}/Component/task/lists/224/LmqJMnZ6'
        title = '获取丰收节-任务列表'
        logger.info(f"\n开始{title}")
        url = url_fsj_taskList
        headers = {'content-type': "application/json", 'User-Agent':User_Agent, 'X-CSRF-TOKEN':csrfToken}
        resp = requests.get(url, headers = headers, cookies=cookie)
        if resp.status_code >= 200 and resp.status_code < 300:
            content = resp.content.decode('utf-8')
            result = json.loads(content, object_hook=customStudentDecoder)
            if(result.status=='success'):
                userTask = result.data.userTask
                taskExecState = False
                for i,task in enumerate(userTask):
                    if(i < taskIndex):
                        continue
                    if(task.finish == 0 and not taskExecState):
                        taskExecState = True
                        t = result.data.task[i]
                        logger.info(f'开始任务：{t.show_set.desc}')
                        link_url = t.link_url
                        logger.info('延时2秒')
                        time.sleep(2)
                        self.fsjDoTask(fsj_domain, cookie, link_url, csrfToken)
                    elif(taskExecState):
                        logger.info('延时5秒')
                        time.sleep(5)
                        self.fsjTask(fsj_domain, cookie, csrfToken, i+1)
                        break
                 
            else:
                logger.info(f'{title}接口返回错误！')
                logger.info(result)
        else:
            logger.info(f'{title}接口调用失败！{resp.status_code}')
            logger.info(resp.content)


    # 丰收节-做任务
    def fsjDoTask(self, fsj_domain, cookie, link_url, csrfToken):
        url = f'{fsj_domain}/oauth/redirect/{link_url[link_url.rfind("/",0,link_url.rfind("?"))+1:len(link_url)]}&returl={parse.quote(link_url,safe="")}'
        resp = requests.get(url, allow_redirects=True, headers = headers, cookies=cookie)
        if(resp.ok):
            cookies = resp.cookies
            # webResult['url']=h.headers['location']
            # logger.info(f'302跳转后服务器地址：{webResult["url"]}')
            # for h in resp.history:
            #     logger.info(f'重定向：\n{h.headers}')
            # content = resp.content.decode('utf-8')
            # logger.info(f'content: {content}')
            self.fsjTaskDelay(link_url, cookies)
        else:
            logger.info(f'{title}接口调用失败！{resp.status_code}')
            logger.info(resp.content)

    def fsjTaskDelay(self, url, cookie):
        url = url.replace('/s/','/getDigitalTimerNum/')
        title = '丰收节-浏览任务'
        logger.info(f"\n开始{title}")
        for i in range(0, 10):
            logger.info('延时1秒')
            time.sleep(1)
            resp = requests.get(url, headers = headers, cookies=cookie)
            if resp.status_code >= 200 and resp.status_code < 300:
                content = resp.content.decode('utf-8')
                result = json.loads(content, object_hook=customStudentDecoder)
                logger.info(result.message)
            else:
                logger.info(f'{title}接口调用失败！{resp.status_code}')
                logger.info(resp.content)
                return

    # 丰收节 - 查询摇骰子次数
    def fsjGetIndex(self, fsj_domain, cookie, csrfToken):
        url_fsj_index = f'{fsj_domain}/activity/dmspthrowluck/getThrowNum/224/LmqJMnZ6'
        title = '丰收节-查询摇骰子次数'
        logger.info(f"\n开始{title}")
        url = url_fsj_index
        headers = {'content-type': "application/json", 'User-Agent':User_Agent, 'X-CSRF-TOKEN':csrfToken}
        resp = requests.get(url,  headers = headers, cookies=cookie)
        if resp.status_code >= 200 and resp.status_code < 300:
            content = resp.content.decode('utf-8')
            result = json.loads(content, object_hook=customStudentDecoder)
            if(result.status=='success'):
                remainNum = int(result.data.remain)
                logger.info(f'共有{remainNum}次摇骰子的机会')
                for i in range(0,remainNum):
                    self.fsjDrawPrize(fsj_domain, cookie, csrfToken)
                    logger.info('延时5秒')
                    time.sleep(5)    
            else:
                logger.info(f'{title}接口返回错误！')
                logger.info(result)
        else:
            logger.info(f'{title}接口调用失败！{resp.status_code}')
            logger.info(resp.content)

    # 丰收节 - 摇骰子
    def fsjDrawPrize(self, fsj_domain, cookie, csrfToken):
        url_fsj_drawPrize=f'{fsj_domain}/activity/dmspthrowluck/draw/224/LmqJMnZ6'
        title = '丰收节摇骰子'
        logger.info(f"\n开始{title}")
        url = url_fsj_drawPrize
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
        else:
            logger.info(f'{title}接口调用失败！{resp.status_code}')
            logger.info(resp.content)

    # 获取丰收节助力码
    def getShareCode(self, fsj_domain, cookie):
        url_fsj_userInfo=f'{fsj_domain}/Common/activity/getUserInfo/224/LmqJMnZ6'
        title = '获取丰收节助力码'
        logger.info(f"\n开始{title}")
        url = url_fsj_userInfo
        headers = {'User-Agent':User_Agent}
        resp = requests.get(url, headers = headers, cookies=cookie)
        if resp.status_code >= 200 and resp.status_code < 300:
            content = resp.content.decode('utf-8')
            result = json.loads(content, object_hook=customStudentDecoder)
            if(result.status=='success'):
                shareCode = result.data.ident
                logger.info(f'助力码：{shareCode}')
                self.ccbCommon.cacheShareData(shareCode, 'fsj')
            else:
                logger.info(f'{title}接口返回错误！')
                logger.info(result)
        else:
            logger.info(f'{title}接口调用失败！{resp.status_code}')
            logger.info(resp.content)

