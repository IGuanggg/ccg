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

#消保知识大考验
shortId_xbzsdky = 'oBFMveSbiyrx-ruPj0VG2g'
#消保知识大考验 题目难度：默认最简单[青铜卫士、白银战士、荣耀卫士、王者归来]
question_level_index = 0

class CcbXbzsdky:

    ccbCommon = None

    #答题、抽奖次数
    runCount = 0
    drawCount = 0
    runStatus = True

    def __init__(self, ccbCommon):
        self.ccbCommon = ccbCommon

    def exec(self):
        #消保知识大考验
        try:
            shareCode = self.ccbCommon.getShareData('xbzsdky')
            redirectResult = self.ccbCommon.requestToken(shortId_xbzsdky, '1000102',u=shareCode)
            redirectUrl = redirectResult['redirectUrl']
            redirectCookie = redirectResult['cookie']
            xbzsdkyResult = self.ccbCommon.captureWebCK(redirectUrl, redirectCookie, '抓取消保知识大考验参数')
            xbzsdky_cookie = xbzsdkyResult['cookie']
            xbzsdky_url = xbzsdkyResult['url']
            xbzsdky_domain = xbzsdky_url[0:xbzsdky_url.find('/',xbzsdky_url.find('://')+3)]
            xbzsdky_csrfToken = xbzsdkyResult['csrfToken']
            self.getShareCode(xbzsdky_domain ,xbzsdky_cookie)
            #回答问题
            self.xbzsdkyLevel(xbzsdky_domain, xbzsdky_cookie, xbzsdky_csrfToken)
            #抽奖
            if(self.ccbCommon.autoChou):
                self.xbzsdkyUserExtInfo(xbzsdky_domain, xbzsdky_cookie, xbzsdky_csrfToken)
        except Exception as e:
            self.runStatus = False
            logger.error('出错了！', e)


    #消保知识大考验 - 查询答题等级
    def xbzsdkyLevel(self, xbzsdky_domain, cookie, csrfToken):
        url_xbzsdky_info=f'{xbzsdky_domain}/Component/answer/getLevels/224/xZ4JppPl'
        title = '查询消保知识大考验答题等级'
        logger.info(f"\n开始{title}")
        url = url_xbzsdky_info
        headers = {'User-Agent':User_Agent, 'X-CSRF-TOKEN':csrfToken}
        resp = requests.get(url, headers = headers, cookies=cookie)
        if resp.status_code >= 200 and resp.status_code < 300:
            content = resp.content.decode('utf-8')
            result = json.loads(content, object_hook=customStudentDecoder)
            # logger.info(result)
            if(result.status=='success'):
                # answer_num 可能是答题次数
                answerNum = int(result.data.answer_num)
                logger.info(f'剩余{answerNum}次答题机会。')
                while answerNum>0:
                    levelData = result.data.list[question_level_index]
                    logger.info(f'选择答题难度：{levelData.level_name}, 共{levelData.reach_num}道题，每题限时{levelData.answer_time}。')
                    level = levelData.level
                    self.xbzsdkyGetQuestions(xbzsdky_domain, cookie, level, csrfToken)
                    answerNum-=1
            else:
                logger.info(f'{title}接口返回错误！')
                logger.info(result)
        else:
            logger.info(f'{title}接口调用失败！{resp.status_code}')
            logger.info(resp.content)

    #消保知识大考验 - 获取题目
    def xbzsdkyGetQuestions(self, xbzsdky_domain, cookie, level, csrfToken):
        url_xbzsdky_questions=f'{xbzsdky_domain}/Component/answer/getQuestions/224/xZ4JppPl'
        title = '获取消保知识大考验题目'
        logger.info(f"\n开始{title}")
        url = url_xbzsdky_questions
        payload = {'id':level}
        headers = {'content-type': "application/json", 'User-Agent':User_Agent, 'X-CSRF-TOKEN':csrfToken}
        resp = requests.post(url, data = json.dumps(payload), headers = headers, cookies=cookie)
        if resp.status_code >= 200 and resp.status_code < 300:
            content = resp.content.decode('utf-8')
            result = json.loads(content, object_hook=customStudentDecoder)
            if(result.status=='success'):
                self.runCount+=1
                self.showQuestion(xbzsdky_domain, cookie, level, result.data[0], csrfToken)
            else:
                logger.info(f'{title}接口返回错误！')
                logger.info(result)
        else:
            logger.info(f'{title}接口调用失败！{resp.status_code}')
            logger.info(resp.content)

    def showQuestion(self, xbzsdky_domain, cookie, level, questionData, csrfToken):
        logger.info(f'{questionData.title}')
        startTime = datetime.now()
        questionId = questionData.questionId
        options = questionData.options
        for step,option in enumerate(options):
            logger.info(f'【{step+1}】、{option.option} ({option.id})')
        #获取答题库
        questionDB = self.ccbCommon.question.getQuestion(questionId, '消保知识大考验')
        # logger.info(f'获取答题库：{questionDB}')
        answerFlag = True
        answerBft =[]
        if(questionDB==None):
            for option in questionData.options:
                answerBft.append(option.id)
            if(self.ccbCommon.ifSubmitQuestion):
                self.ccbCommon.question.submitQuestion(questionData, "消保知识大考验")
        else:
            for answer in questionDB.answerList:
                if(answer.result == 1):
                    answerFlag = False
                    # logger.info(f'答题： questionId ： {questionId}， options : {answer.id}')
                    self.xbzsdkyDo(xbzsdky_domain, cookie,questionId , level, answer.id, csrfToken, startTime)
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
                self.xbzsdkyDo(xbzsdky_domain, cookie,questionId , level, options[x-1].id, csrfToken, startTime)
        else:
             # answerFlag = True, 表示答题库没有正确答案，需要将提交的结果写入到答题库中
            # logger.info(f'答题： questionId ： {questionId}， options : {answerBft[0]}')
            answerIndex = random.randint(0, len(answerBft)-1)
            logger.info(f'未匹配到答案， 随机选择：【{answerIndex}】')
            self.xbzsdkyDo(xbzsdky_domain, cookie,questionId , level, answerBft[answerIndex], csrfToken, startTime)

    #消保知识大考验 - 提交答案
    def xbzsdkyDo(self, xbzsdky_domain, cookie, id, levelId, options, csrfToken, startTime):
        nowTime = datetime.now()
        delay = 5 - (nowTime-startTime).seconds
        if(delay>0):
            logger.info(f'延迟{delay}秒后再提交答案')
            time.sleep(delay)
        url_xbzsdky_do=f'{xbzsdky_domain}/Component/answer/do/224/xZ4JppPl'
        title = '提交消保知识大考验题目答案'
        logger.info(f"\n开始{title}")
        url = url_xbzsdky_do
        payload = {'id':id, 'levelId':levelId, 'options':options}
        headers = {'content-type': "application/json", 'User-Agent':User_Agent, 'X-CSRF-TOKEN':csrfToken}
        resp = requests.post(url, data = json.dumps(payload), headers = headers, cookies=cookie)
        if resp.status_code >= 200 and resp.status_code < 300:
            content = resp.content.decode('utf-8')
            result = json.loads(content, object_hook=customStudentDecoder)
            try:                 
                try:
                    rights = result.data.rights  
                    for r in rights:
                        self.ccbCommon.question.submitQuestionAnswer(id, r, 1)
                        logger.info(f'{"回答正确！" if options ==r else "回答错误！"}')
                except Exception as e1:
                    logger.error(e1)
                #判断是否是最后一题
                if(result.data.isEnd==0):
                    #继续回答下一题
                    self.showQuestion(xbzsdky_domain, cookie, levelId, result.data.next, csrfToken)
                else:
                    #查询回答结果
                    self.xbzsdkyGetResult(xbzsdky_domain, cookie, levelId, csrfToken)
            except Exception as e:
                logger.error(f'{title}接口处理异常！',e)
        else:
            logger.info(f'{title}接口调用失败！{resp.status_code}')
            logger.info(resp.content)

    #消保知识大考验 - 查询答题结果        
    def xbzsdkyGetResult(self, xbzsdky_domain, cookie, level, csrfToken):
        url_xbzsdky_getResult = f'{xbzsdky_domain}/Component/answer/getResult/224/xZ4JppPl'
        title = '查询消保知识大考验答题结果'
        logger.info(f"\n开始{title}")
        url = url_xbzsdky_getResult
        headers = {'content-type': "application/json", 'User-Agent':User_Agent, 'X-CSRF-TOKEN':csrfToken}
        payload = {'id':level}
        resp = requests.post(url, data = json.dumps(payload), headers = headers, cookies=cookie)
        if resp.status_code >= 200 and resp.status_code < 300:
            content = resp.content.decode('utf-8')
            result = json.loads(content, object_hook=customStudentDecoder)
            if(result.status=='success'):
                logger.info(f'消保知识大考验答题结果:{"通过" if(result.data.status==1) else "失败"}，共答对{result.data.rights}题，答错{result.data.failts}次')
                
            else:
                logger.info(f'{title}接口返回错误！')
                logger.info(result)
        else:
            logger.info(f'{title}接口调用失败！{resp.status_code}')
            logger.info(resp.content)


    #消保知识大考验 - 查询抽奖次数
    def xbzsdkyUserExtInfo(self, xbzsdky_domain, cookie, csrfToken):
        url_xbzsdky_getUserExtInfo=f'{xbzsdky_domain}/Component/draw/getUserExtInfo/224/xZ4JppPl'
        title = '查询消保知识大考验抽奖次数'
        logger.info(f"\n开始{title}")
        url = url_xbzsdky_getUserExtInfo
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
                    self.xbzsdkyDrawPrize(xbzsdky_domain, cookie, csrfToken)
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

    #消保知识大考验 - 抽奖
    def xbzsdkyDrawPrize(self, xbzsdky_domain, cookie, csrfToken):
        url_xbzsdky_commonDrawPrize=f'{xbzsdky_domain}/Component/draw/commonDrawPrize/224/xZ4JppPl'
        title = '消保知识大考验抽奖'
        logger.info(f"\n开始{title}")
        url = url_xbzsdky_commonDrawPrize
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


    # 获取消保知识大考验助力码
    def getShareCode(self, xbzsdky_domain, cookie):
        url_xbzsdky_userInfo=f'{xbzsdky_domain}/Common/activity/getUserInfo/224/xZ4JppPl'
        title = '获取消保知识大考验助力码'
        logger.info(f"\n开始{title}")
        url = url_xbzsdky_userInfo
        headers = {'User-Agent':User_Agent}
        resp = requests.get(url, headers = headers, cookies=cookie)
        if resp.status_code >= 200 and resp.status_code < 300:
            content = resp.content.decode('utf-8')
            result = json.loads(content, object_hook=customStudentDecoder)
            if(result.status=='success'):
                shareCode = result.data.ident
                logger.info(f'助力码：{shareCode}')
                self.ccbCommon.cacheShareData(shareCode, 'xbzsdky')
            else:
                logger.info(f'{title}接口返回错误！')
                logger.info(result)
        else:
            logger.info(f'{title}接口调用失败！{resp.status_code}')
            logger.info(resp.content)