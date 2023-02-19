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

#跨境专区
shortId_kjzq = 'rhak6Z7RK5POrVshh6xCuw'

class CcbKjzq:

    ccbCommon = None

    #答题、抽奖次数
    runCount = 0
    drawCount = 0
    runStatus = True
    
    #授权状态：
    authStatus = True
    
    def __init__(self, ccbCommon):
        self.ccbCommon = ccbCommon

    def exec(self):
        #跨境专区
        try:
            shareCode = self.ccbCommon.getShareData('kjzq')
            redirectResult = self.ccbCommon.requestToken(shortId_kjzq, '1000102',u=shareCode)
            redirectUrl = redirectResult['redirectUrl']
            redirectCookie = redirectResult['cookie']
            if(redirectUrl.find('__dmsp_token')==-1):
                logger.info(f'无效的登录链接{redirectUrl}')
            kjzqResult = self.ccbCommon.captureWebCK(redirectUrl, redirectCookie, '抓取跨境专区参数')
            kjzq_cookie = kjzqResult['cookie']
            kjzq_url = kjzqResult['url']
            kjzq_domain = kjzq_url[0:kjzq_url.find('/',kjzq_url.find('://')+3)]
            kjzq_csrfToken = kjzqResult['csrfToken']
            self.getShareCode(kjzq_domain ,kjzq_cookie)
            if(self.authStatus):
                #回答问题
                self.kjzqInfo(kjzq_domain, kjzq_cookie, kjzq_csrfToken)
                # #抽奖
                if(self.ccbCommon.autoChou):
                    self.kjzqUserExtInfo(kjzq_domain, kjzq_cookie, kjzq_csrfToken)
            else:
                logger.info(f'当前活动未授权，跳过。')
        except Exception as e:
            self.runStatus = False
            logger.error('出错了！', e)

    #跨境专区 - 查询答题等级
    def kjzqInfo(self, kjzq_domain, cookie, csrfToken):
        url_kjzq_info=f'{kjzq_domain}/Component/answer/getLevels/224/gPpYRemE'
        title = '查询跨境专区答题等级'
        logger.info(f"\n开始{title}")
        url = url_kjzq_info
        headers = {'User-Agent':User_Agent, 'X-CSRF-TOKEN':csrfToken}
        resp = requests.get(url, headers = headers, cookies=cookie)
        if resp.status_code >= 200 and resp.status_code < 300:
            content = resp.content.decode('utf-8')
            result = json.loads(content, object_hook=customStudentDecoder)
            # logger.info(result)
            if(result.status=='success'):
                level = result.data.list[0].level
                # answer_num 可能是答题次数
                answerNum = result.data.answer_num
                logger.info(f'level：{level} , answerNum : {answerNum} ')
                if(int(answerNum)>0):
                    self.kjzGetQuestions(kjzq_domain, cookie, level, csrfToken)
            else:
                logger.info(f'{title}接口返回错误！')
                logger.info(result)
        else:
            logger.info(f'{title}接口调用失败！{resp.status_code}')
            logger.info(resp.content)

    #跨境专区 - 获取题目
    def kjzGetQuestions(self, kjzq_domain, cookie, level, csrfToken):
        startTime = datetime.now()
        url_kjzq_questions=f'{kjzq_domain}/Component/answer/getQuestions/224/gPpYRemE'
        title = '获取跨境专区题目'
        logger.info(f"\n开始{title}")
        url = url_kjzq_questions
        payload = {'id':level}
        headers = {'content-type': "application/json", 'User-Agent':User_Agent, 'X-CSRF-TOKEN':csrfToken}
        resp = requests.post(url, data = json.dumps(payload), headers = headers, cookies=cookie)
        if resp.status_code >= 200 and resp.status_code < 300:
            self.runCount+=1
            content = resp.content.decode('utf-8')
            result = json.loads(content, object_hook=customStudentDecoder)
            if(result.status=='success'):
                self.showQuestion(kjzq_domain, cookie, level, result.data[0], csrfToken)
            else:
                logger.info(f'{title}接口返回错误！')
                logger.info(result)
        else:
            logger.info(f'{title}接口调用失败！{resp.status_code}')
            logger.info(resp.content)

    def showQuestion(self, kjzq_domain, cookie, level, questionData, csrfToken):
        questionId = questionData.questionId
        logger.info(f'{questionData.title} ({questionId})，【{level}】')
        startTime = datetime.now()
        options = questionData.options
        for step,option in enumerate(options):
            logger.info(f'【{step+1}】、{option.option} ({option.id})')
        #获取答题库
        questionDB = self.ccbCommon.question.getQuestion(questionId, '跨境专区')
        # logger.info(f'获取答题库：{questionDB}')
        answerFlag = True
        answerBft =[]
        if(questionDB==None):
            for option in questionData.options:
                answerBft.append(option.id)
            if(self.ccbCommon.ifSubmitQuestion):
                self.ccbCommon.question.submitQuestion(questionData, "跨境专区")
        else:
            for answer in questionDB.answerList:
                if(answer.result == 1):
                    answerFlag = False
                    # logger.info(f'答题： questionId ： {questionId}， options : {answer.id}')
                    self.kjzDo(kjzq_domain, cookie,questionId , level, answer.id, csrfToken, startTime, 0)
                    return
                elif(answer.result == 0):
                    answerBft.append(answer.id)
        if(self.ccbCommon.ifCMDAnswerQuestions):
                logger.info('----------------限时30秒----------------------')
                x = -1
                while x<0 or x > len(options):
                    logger.info('请输入选择的答案序号：')
                    try:
                        x = int(input())
                    except:
                        logger.info(f'请输入数字，且在【1-{len(options)}】范围内！')
                # logger.info(f'答题： questionId ： {questionId}， options : {options[x-1].id}')
                self.kjzDo(kjzq_domain, cookie,questionId , level, options[x-1].id, csrfToken, startTime, 0)
        else:
             # answerFlag = True, 表示答题库没有正确答案，需要将提交的结果写入到答题库中
            # logger.info(f'答题： questionId ： {questionId}， options : {answerBft[0]}')
            answerIndex = random.randint(0, len(answerBft)-1)
            logger.info(f'未匹配到答案， 随机选择：【{answerIndex}】')
            self.kjzDo(kjzq_domain, cookie,questionId , level, answerBft[answerIndex], csrfToken, startTime, 0)

    #跨境专区 - 提交答案
    def kjzDo(self, kjzq_domain, cookie, id, levelId, options, csrfToken, startTime, retry):
        nowTime = datetime.now()
        delay = 4 - (nowTime-startTime).seconds
        if(delay>0):
            logger.info(f'延迟{delay}秒后再提交答案')
            time.sleep(delay)
        url_kjzq_do=f'{kjzq_domain}/Component/answer/do/224/gPpYRemE'
        title = '提交跨境专区题目答案'
        logger.info(f"\n开始{title}")
        url = url_kjzq_do
        payload = {'id':id, 'levelId':levelId, 'options':options}
        headers = {'content-type': "application/json", 'User-Agent':User_Agent, 'X-CSRF-TOKEN':csrfToken}
        resp = requests.post(url, data = json.dumps(payload), headers = headers, cookies=cookie)
        if resp.status_code >= 200 and resp.status_code < 300:
            content = resp.content.decode('utf-8')
            if(content.find('活动太火爆')>-1 and retry<3):
                logger.info('活动太火爆了,延时2秒后再次尝试提交。')
                time.sleep(2)
                self.kjzDo(kjzq_domain, cookie, id, levelId, options, csrfToken, startTime, retry+1)
                return
            result = json.loads(content, object_hook=customStudentDecoder)
            try:
                rights = result.data.rights
                for r in rights:
                    self.ccbCommon.question.submitQuestionAnswer(id, r, 1)
                    logger.info(f'{"回答正确！" if options ==r else "回答错误！"}')
            except Exception as e:
                logger.error(f'{title}接口处理异常！')
        else:
            logger.info(f'{title}接口调用失败！{resp.status_code}')
            logger.info(resp.content)

    #跨境专区 - 查询抽奖次数
    def kjzqUserExtInfo(self, kjzq_domain, cookie, csrfToken):
        url_kjzq_getUserExtInfo=f'{kjzq_domain}/Component/draw/getUserExtInfo/224/gPpYRemE'
        title = '查询跨境专区抽奖次数'
        logger.info(f"\n开始{title}")
        url = url_kjzq_getUserExtInfo
        headers = {'content-type': "application/json", 'User-Agent':User_Agent, 'X-CSRF-TOKEN':csrfToken}
        resp = requests.get(url, headers = headers, cookies=cookie)
        if resp.status_code >= 200 and resp.status_code < 300:
            content = resp.content.decode('utf-8')
            result = json.loads(content, object_hook=customStudentDecoder)
            if(result.status=='success'):
                remainNum = int(result.data.remain_num)
                logger.info(f"跨境专区抽奖次数:{remainNum}次")
                while remainNum>0:
                    #抽奖
                    self.kjzqDrawPrize(kjzq_domain, cookie, csrfToken)
                    remainNum -= 1
                    if(remainNum>0):
                        logger.info('延时5秒')
                        time.sleep(5)
            else:
                logger.info(f'{title}接口返回错误！')
                logger.info(result)
        else:
            logger.info(f'{title}接口调用失败！{resp.status_code}')
            logger.info(resp.content)

    #跨境专区 - 抽奖
    def kjzqDrawPrize(self, kjzq_domain, cookie, csrfToken):
        url_kjzq_commonDrawPrize=f'{kjzq_domain}/Component/draw/commonDrawPrize/224/gPpYRemE'
        title = '跨境专区抽奖'
        logger.info(f"\n开始{title}")
        url = url_kjzq_commonDrawPrize
        headers = {'content-type': "application/json", 'User-Agent':User_Agent, 'X-CSRF-TOKEN':csrfToken}
        resp = requests.post(url, data='{}', headers = headers, cookies=cookie)
        if resp.status_code >= 200 and resp.status_code < 300:
            self.drawCount+=1
            content = resp.content.decode('utf-8')
            result = json.loads(content, object_hook=customStudentDecoder)
            if(result.status=='success'):
                logger.info(f"{result.message} , {result.data.prizename}")
            else:
                logger.info(f'{title}接口返回错误！')
                logger.info(result)
        else:
            logger.info(f'{title}接口调用失败！{resp.status_code}')
            logger.info(resp.content)   

    # 获取跨境专区助力码
    def getShareCode(self, kjzq_domain, cookie):
        url_kjzq_userInfo=f'{kjzq_domain}/Common/activity/getUserInfo/224/gPpYRemE'
        title = '获取跨境专区助力码'
        logger.info(f"\n开始{title}")
        url = url_kjzq_userInfo
        headers = {'User-Agent':User_Agent}
        resp = requests.get(url, headers = headers, cookies=cookie)
        if resp.status_code >= 200 and resp.status_code < 300:
            content = resp.content.decode('utf-8')
            logger.info(content)
            result = json.loads(content, object_hook=customStudentDecoder)
            if(result.status=='success'):
                shareCode = result.data.ident
                logger.info(f'助力码：{shareCode}')
                self.ccbCommon.cacheShareData(shareCode, 'kjzq')
            elif(result.status=='fail' and content.find('未授权')>-1):
                logger.info(result)
                self.authStatus = False
            else:
                logger.info(f'{title}接口返回错误！')
                logger.info(result)
        else:
            logger.info(f'{title}接口调用失败！{resp.status_code}')
            logger.info(resp.content)
