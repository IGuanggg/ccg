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

# 商户专区 - 摇骰子
shortId_shzq = 'iqHcVYOrNXsfnKaLOmZAlA'

class CcbShzq:

    ccbCommon = None

    #掷骰子次数
    drawCount = 0
    runStatus = True

    def __init__(self, ccbCommon):
        self.ccbCommon = ccbCommon

    def exec(self):
        #商户专区
        try:
            redirectResult = self.ccbCommon.requestToken(shortId_shzq, '6000111')
            redirectUrl = redirectResult['redirectUrl']
            redirectCookie = redirectResult['cookie']
            # logger.info(f"养老模块redirectUrl：{redirectUrl}")
            shzqResult = self.ccbCommon.captureWebCK(redirectUrl, redirectCookie, '抓取养老打卡签到参数') # home_domain, yldk_domain,
            shzq_cookie = shzqResult['cookie']
            shzq_url = shzqResult['url']
            shzq_domain = shzq_url[0:shzq_url.find('/',shzq_url.find('://')+3)]
            shzq_csrfToken = shzqResult['csrfToken']
            self.shzqTask(shzq_domain ,shzq_cookie, shzq_csrfToken)
            self.shzqGetIndex(shzq_domain, shzq_cookie, shzq_csrfToken)
        except Exception as e:
            self.runStatus = False
            logger.error('出错了！', e)


    #获取商户专区-任务列表
    def shzqTask(self, shzq_domain, cookie, csrfToken):
        url_shzq_taskList=f'{shzq_domain}/Component/task/lists/224/vmKOQvm1'
        title = '获取商户专区-任务列表'
        logger.info(f"\n开始{title}")
        url = url_shzq_taskList
        headers = {'content-type': "application/json", 'User-Agent':User_Agent, 'X-CSRF-TOKEN':csrfToken}
        resp = requests.get(url, headers = headers, cookies=cookie)
        if resp.status_code >= 200 and resp.status_code < 300:
            content = resp.content.decode('utf-8')
            result = json.loads(content, object_hook=customStudentDecoder)
            if(result.status=='success'):
                userTask = result.data.userTask
                for task in userTask:
                    if(task.finish == 0):
                        taskId = task.id
                        self.shzqDoTask(shzq_domain, cookie, taskId, csrfToken)
                        logger.info('延时5秒')
                        time.sleep(5)    

            else:
                logger.info(f'{title}接口返回错误！')
                logger.info(result)
        else:
            logger.info(f'{title}接口调用失败！{resp.status_code}')
            logger.info(resp.content)


    # 商户专区-做任务
    def shzqDoTask(self, shzq_domain, cookie, taskId, csrfToken):
        url_shzq_doTask=f'{shzq_domain}/Component/task/do/224/vmKOQvm1'
        title = '商户专区-做任务'
        logger.info(f"\n开始{title}")
        url = url_shzq_doTask
        payload = {'id':taskId}
        headers = {'content-type': "application/json", 'User-Agent':User_Agent, 'X-CSRF-TOKEN':csrfToken}
        resp = requests.post(url, data = json.dumps(payload), headers = headers, cookies=cookie)
        if resp.status_code >= 200 and resp.status_code < 300:
            content = resp.content.decode('utf-8')
            logger.info(urllib.parse.unquote(content))
        else:
            logger.info(f'{title}接口调用失败！{resp.status_code}')
            logger.info(resp.content)


    # 商户专区 - 查询摇骰子次数
    def shzqGetIndex(self, shzq_domain, cookie, csrfToken):
        url_shzq_index = f'{shzq_domain}/activity/dmspshzq/getIndex/224/vmKOQvm1'
        title = '商户专区-查询摇骰子次数'
        logger.info(f"\n开始{title}")
        url = url_shzq_index
        headers = {'content-type': "application/json", 'User-Agent':User_Agent, 'X-CSRF-TOKEN':csrfToken}
        resp = requests.get(url,  headers = headers, cookies=cookie)
        if resp.status_code >= 200 and resp.status_code < 300:
            content = resp.content.decode('utf-8')
            result = json.loads(content, object_hook=customStudentDecoder)
            if(result.status=='success'):
                remainNum = int(result.data.remain_num)
                logger.info(f'共有{remainNum}次摇骰子的机会')
                for i in range(0,remainNum):
                    self.shzqDrawPrize(shzq_domain, cookie, csrfToken)
                    logger.info('延时8秒')
                    time.sleep(8)    
            else:
                logger.info(f'{title}接口返回错误！')
                logger.info(result)
        else:
            logger.info(f'{title}接口调用失败！{resp.status_code}')
            logger.info(resp.content)

    # 商户专区 - 摇骰子
    def shzqDrawPrize(self, shzq_domain, cookie, csrfToken):
        url_shzq_drawPrize=f'{shzq_domain}/activity/dmspshzq/drawPrize/224/vmKOQvm1'
        title = '商户专区摇骰子'
        logger.info(f"\n开始{title}")
        url = url_shzq_drawPrize
        headers = {'content-type': "application/json", 'User-Agent':User_Agent, 'X-CSRF-TOKEN':csrfToken}
        resp = requests.post(url, data='{}', headers = headers, cookies=cookie)
        if resp.status_code >= 200 and resp.status_code < 300:
            self.drawCount+=1
            content = resp.content.decode('utf-8')
            result = json.loads(content, object_hook=customStudentDecoder)
            if(result.status=='success'):
                logger.info(f"{result.message} , {result.data.prize_name}")
            else:
                logger.info(f'{title}接口返回错误！')
                logger.info(result)
        else:
            logger.info(f'{title}接口调用失败！{resp.status_code}')
            logger.info(resp.content)