from ccb_common import CcbCommon
from ccb_home import CcbHome
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

#消保牛牛大闯关
shortId_xbnndcg = 'kILf9FkIztC2SP1F71lOYg'
#消保牛牛大闯关 
question_level_index = 0

class CcbXbnndcg:

    ccbCommon = None

    #答题、抽奖次数
    runCount = 0
    drawCount = 0
    runStatus = True

    def __init__(self, ccbCommon):
        self.ccbCommon = ccbCommon

    def exec(self):
        #消保牛牛大闯关
        try:
            shareCode = self.ccbCommon.getShareData('xbnndcg')
            redirectResult = self.ccbCommon.requestToken(shortId_xbnndcg, '1000102',u=shareCode)
            redirectUrl = redirectResult['redirectUrl']
            redirectCookie = redirectResult['cookie']
            xbnndcgResult = self.ccbCommon.captureWebCK(redirectUrl, redirectCookie, '抓取消保牛牛大闯关参数')
            xbnndcg_cookie = xbnndcgResult['cookie']
            xbnndcg_url = xbnndcgResult['url']
            xbnndcg_domain = xbnndcg_url[0:xbnndcg_url.find('/',xbnndcg_url.find('://')+3)]
            xbnndcg_csrfToken = xbnndcgResult['csrfToken']
            self.getShareCode(xbnndcg_domain ,xbnndcg_cookie)
            #答题次数
            self.xbnndcgRemain(xbnndcg_domain, xbnndcg_cookie, xbnndcg_csrfToken)
            #抽奖
            if(self.ccbCommon.autoChou):
                self.xbnndcgUserExtInfo(xbnndcg_domain, xbnndcg_cookie, xbnndcg_csrfToken)
        except Exception as e:
            self.runStatus = False
            logger.error('出错了！', e)
            
    #消保牛牛大闯关 - 查询答题次数
    def xbnndcgRemain(self, xbnndcg_domain, cookie, csrfToken):
        url_xbnndcg_remain=f'{xbnndcg_domain}/activity/dmspxbnnanswer/getChance/224/6321AWZe'
        title = '查询消保牛牛大闯关答题次数'
        logger.info(f"\n开始{title}")
        url = url_xbnndcg_remain
        headers = {'User-Agent':User_Agent, 'X-CSRF-TOKEN':csrfToken}
        resp = requests.get(url, headers = headers, cookies=cookie)
        if resp.status_code >= 200 and resp.status_code < 300:
            content = resp.content.decode('utf-8')
            # logger.info(content)
            result = json.loads(content, object_hook=customStudentDecoder)
            # logger.info(result)
            if(result.status=='success'):
                # remain 可能是答题次数
                remain = int(result.data.remain)
                logger.info(f'剩余{remain}次答题机会。')
                while remain>0:
                    remain-=1
                    self.runCount+=1
                    self.xbnndcgLevel(xbnndcg_domain, cookie, csrfToken)
                    if(remain>0):
                        logger.info('延时3秒')
                        time.sleep(3)
            else:
                logger.info(f'{title}接口返回错误！')
                logger.info(result)
        else:
            logger.info(f'{title}接口调用失败！{resp.status_code}')
            logger.info(resp.content)

    #消保牛牛大闯关 - 查询答题关卡
    def xbnndcgLevel(self, xbnndcg_domain, cookie, csrfToken):
        url_xbnndcg_level=f'{xbnndcg_domain}/activity/dmspxbnnanswer/levelList/224/6321AWZe'
        title = '查询消保牛牛大闯关答题关卡'
        logger.info(f"\n开始{title}")
        url = url_xbnndcg_level
        headers = {'User-Agent':User_Agent, 'X-CSRF-TOKEN':csrfToken}
        resp = requests.get(url, headers = headers, cookies=cookie)
        if resp.status_code >= 200 and resp.status_code < 300:
            content = resp.content.decode('utf-8')
            result = json.loads(content, object_hook=customStudentDecoder)
            # logger.info(content)
            if(result.status=='success'):
                for i,levelData in enumerate(reversed(result.data)):
                    if(levelData.status==3):
                        logger.info(f"\n开始{levelData.name}")
                        self.xbnndcgGetQuestions(xbnndcg_domain, cookie, levelData.bout, levelData.questionNo, levelData.mark, csrfToken)
                        return
                    #elif(levelData.status==1):
                        #logger.info(f'{levelData.name}已通过')
                    elif(levelData.status!=4 and levelData.status!=1):
                        logger.info(f'关卡状态？？<{levelData}>')
            else:
                logger.info(f'{title}接口返回错误！')
                logger.info(result)
        else:
            logger.info(f'{title}接口调用失败！{resp.status_code}')
            logger.info(resp.content)

    #消保牛牛大闯关 - 获取题目
    def xbnndcgGetQuestions(self, xbnndcg_domain, cookie, boutId, questionNo, levelId, csrfToken):
        url_xbnndcg_questions=f'{xbnndcg_domain}/activity/dmspxbnnanswer/getQuestion/224/6321AWZe?boutId={boutId}&levelId={levelId}&questionNo={questionNo}'
        title = '获取消保牛牛大闯关题目'
        logger.info(f"\n开始{title}")
        url = url_xbnndcg_questions
        headers = {'content-type': "application/json", 'User-Agent':User_Agent, 'X-CSRF-TOKEN':csrfToken}
        resp = requests.get(url, headers = headers, cookies=cookie)
        if resp.status_code >= 200 and resp.status_code < 300:
            content = resp.content.decode('utf-8')
            result = json.loads(content, object_hook=customStudentDecoder)
            if(result.status=='success'):
                self.showQuestion(xbnndcg_domain, cookie, boutId, questionNo, levelId, result.data, csrfToken)
            else:
                logger.info(f'{title}接口返回错误！')
                logger.info(result)
        else:
            logger.info(f'{title}接口调用失败！{resp.status_code}')
            logger.info(resp.content)

    def showQuestion(self, xbnndcg_domain, cookie, boutId, questionNo, levelId, questionData, csrfToken):
        logger.info(f'{questionData.title}')
        startTime = datetime.now()
        #questionId = f'{questionData.boutId}_{questionData.level}_{questionData.question_no}'
        questionId = questionData.start_time
        options = questionData.options
        for step,option in enumerate(options):
            logger.info(f'【{step+1}】、{option.title} ({option.id})')
        #获取答题库
        #questionDB = self.ccbCommon.question.getQuestion(questionId, '消保牛牛大闯关')
        questionDB = self.ccbCommon.question.getQuestionName(questionData.title, '消保牛牛大闯关')
        # logger.info(f'获取答题库：{questionDB}')
        answerFlag = True
        answerBft =[]
        if(questionDB==None):
            for option in questionData.options:
                answerBft.append(option.id)
            if(self.ccbCommon.ifSubmitQuestion):
                self.ccbCommon.question.submitQuestion(questionData, "消保牛牛大闯关")
        else:
            questionId = questionDB.question.question_id
            for answer in questionDB.answerList:
                if(answer.result == 1):
                    #核对答案ID是否一致
                    rf = False
                    for r in questionData.options:
                        if(r.id == answer.id):
                            rf = True
                            break
                    if(rf):
                        answerFlag = False
                        # logger.info(f'答题： questionId ： {questionId}， options : {answer.id}')
                        self.xbnndcgDo(xbnndcg_domain, cookie , questionId, boutId, questionNo, levelId, answer.id, questionData.question_num, csrfToken, startTime, 0)
                        return
                if(answer.result == 0):
                    answerBft.append(answer.id)
        if(len(answerBft)>1 and self.ccbCommon.ifCMDAnswerQuestions):
                logger.info('----------------限时30秒----------------------')
                x = -1
                while x<0 or x > len(options):
                    logger.info('请输入选择的答案序号：')
                    try:
                        x = int(input())
                    except:
                        logger.info(f'请输入数字，且在【1-{len(options)}】范围内！')
                # logger.info(f'答题： questionId ： {questionId}， options : {options[x-1].id}')
                self.xbnndcgDo(xbnndcg_domain, cookie , questionId, boutId, questionNo, levelId, options[x-1].id, questionData.question_num, csrfToken, startTime, 0)
        else:
             # answerFlag = True, 表示答题库没有正确答案，需要将提交的结果写入到答题库中
            # logger.info(f'答题： questionId ： {questionId}， options : {answerBft[0]}')
            answerIndex = random.randint(0, len(answerBft)-1)
            logger.info(f'未匹配到答案， 随机选择：【{answerIndex}】')
            self.xbnndcgDo(xbnndcg_domain, cookie , questionId, boutId, questionNo, levelId, answerBft[answerIndex], questionData.question_num, csrfToken, startTime, 0)

    #消保牛牛大闯关 - 提交答案
    def xbnndcgDo(self, xbnndcg_domain, cookie , questionId, boutId, questionNo, levelId, options, questionNum, csrfToken, startTime, retry):
        nowTime = datetime.now()
        delay = (4+random.randint(0,3)) - (nowTime-startTime).seconds
        if(delay>0):
            logger.info(f'延迟{delay}秒后再提交答案')
            time.sleep(delay)
        url_xbnndcg_do=f'{xbnndcg_domain}/activity/dmspxbnnanswer/submitAnswer/224/6321AWZe'
        title = '提交消保牛牛大闯关题目答案'
        logger.info(f"\n开始{title}")
        url = url_xbnndcg_do
        payload = {'levelId':levelId, 'questionNo':questionNo, 'answer':options, 'boutId':boutId}
        headers = {'content-type': "application/json", 'User-Agent':User_Agent, 'X-CSRF-TOKEN':csrfToken}
        resp = requests.post(url, data = json.dumps(payload), headers = headers, cookies=cookie)
        if resp.status_code >= 200 and resp.status_code < 300:
            content = resp.content.decode('utf-8')
            if(content.find('活动太火爆')>-1 and retry<3):
                logger.info('活动太火爆了,延时1秒后再次重新刷新关卡状态。')
                time.sleep(1)
                self.xbnndcgLevel(xbnndcg_domain, cookie, csrfToken)
                #self.xbnndcgDo(xbnndcg_domain, cookie , questionId, boutId, questionNo, levelId, options, questionNum, csrfToken, startTime, retry+1)
                return
            result = json.loads(content, object_hook=customStudentDecoder)
            try:                 
                logger.info(result.message)
                try:
                    status = result.data.answer_status
                    self.ccbCommon.question.submitQuestionAnswer(questionId, options, 1 if status==1 else -1)
                except Exception as e1:
                    logger.error(e1)
                #判断是否是当前关卡的最后一题
                if(questionNo<questionNum):
                    logger.info('延时1秒')
                    time.sleep(1)
                    self.xbnndcgGetQuestions(xbnndcg_domain, cookie , boutId, questionNo+1, levelId, csrfToken)
                else: #(result.data.level_status==0) 闯关失败！
                    logger.info(f'当前关卡闯关{"成功！" if result.data.level_status==1 else "失败！"}')
                    if(result.data.level_status==1):
                        logger.info('延时3秒')
                        time.sleep(3)
                        if(int(result.data.level_id)<5):
                            self.xbnndcgLevel(xbnndcg_domain, cookie, csrfToken)
            except Exception as e:
                logger.error(f'{title}接口处理异常！',e)
        else:
            logger.info(f'{title}接口调用失败！{resp.status_code}')
            logger.info(resp.content)


    #消保牛牛大闯关 - 查询抽奖次数
    def xbnndcgUserExtInfo(self, xbnndcg_domain, cookie, csrfToken):
        url_xbnndcg_getUserExtInfo=f'{xbnndcg_domain}/Component/draw/getUserExtInfo/224/6321AWZe'
        title = '查询消保牛牛大闯关抽奖次数'
        logger.info(f"\n开始{title}")
        url = url_xbnndcg_getUserExtInfo
        headers = {'content-type': "application/json", 'User-Agent':User_Agent, 'X-CSRF-TOKEN':csrfToken}
        resp = requests.get(url, headers = headers, cookies=cookie)
        if resp.status_code >= 200 and resp.status_code < 300:
            content = resp.content.decode('utf-8')
            result = json.loads(content, object_hook=customStudentDecoder)
            if(result.status=='success'):
                remainNum = int(result.data.remain_num)
                logger.info(f"消保牛牛大闯关抽奖次数:{remainNum}次")
                while remainNum>0:
                    #抽奖
                    self.xbnndcgDrawPrize(xbnndcg_domain, cookie, csrfToken)
                    remainNum -= 1
                    if(remainNum>0):
                        logger.info('延时8秒')
                        time.sleep(8)
            else:
                logger.info(f'{title}接口返回错误！')
                logger.info(result)
        else:
            logger.info(f'{title}接口调用失败！{resp.status_code}')
            logger.info(resp.content)

    #消保牛牛大闯关 - 抽奖
    def xbnndcgDrawPrize(self, xbnndcg_domain, cookie, csrfToken):
        url_xbnndcg_commonDrawPrize=f'{xbnndcg_domain}/Component/draw/commonDrawPrize/224/6321AWZe'
        title = '消保牛牛大闯关抽奖'
        logger.info(f"\n开始{title}")
        url = url_xbnndcg_commonDrawPrize
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


    # 获取消保牛牛大闯关助力码
    def getShareCode(self, xbnndcg_domain, cookie):
        url_xbnndcg_userInfo=f'{xbnndcg_domain}/Common/activity/getUserInfo/224/6321AWZe'
        title = '获取消保牛牛大闯关助力码'
        logger.info(f"\n开始{title}")
        url = url_xbnndcg_userInfo
        headers = {'User-Agent':User_Agent}
        resp = requests.get(url, headers = headers, cookies=cookie)
        if resp.status_code >= 200 and resp.status_code < 300:
            content = resp.content.decode('utf-8')
            result = json.loads(content, object_hook=customStudentDecoder)
            if(result.status=='success'):
                shareCode = result.data.ident
                logger.info(f'助力码：{shareCode}')
                self.ccbCommon.cacheShareData(shareCode, 'xbnndcg')
            else:
                logger.info(f'{title}接口返回错误！')
                logger.info(result)
        else:
            logger.info(f'{title}接口调用失败！{resp.status_code}')
            logger.info(resp.content)