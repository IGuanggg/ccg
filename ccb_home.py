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

# 通过公众号连接，跳转的url（https://event.ccbft.com/e/ccb_gjb/polFsWD2jPnjhOx9ruVBcA?CCB_Chnl=1000102），截取链接最后的地址字符串
shortId = 'polFsWD2jPnjhOx9ruVBcA'

class CcbHome:

    ccbCommon = None

    def __init__(self, ccbCommon):
        self.ccbCommon = ccbCommon


    userId = None
    userName = None
    token = None
    initCcbCount = None

    def exec(self):
        #首页模块
        redirectUrl = self.ccbCommon.requestToken(shortId, '1000102')['redirectUrl']
        self.token = self.getToken(redirectUrl)
        if(self.token == None):
            logger.info('获取Token失败，请检查后重试！')
            return
        #延时500耗秒
        time.sleep(1)
        self.login(self.token)

    def execCCB(self, token):
        try:
            self.token = token
            self.userId = self.getUser(self.token)
            self.ccbCommon.userId = self.userId
            self.initCcbCount = self.userCCD(self.token)
            if(self.userId == None):
                logger.info('userId = None , 无法领取每日奖励金')
            else:
                #领取每日首页cc币 -> 领取每日奖励金
                self.userState(self.token, self.receiveLevelReward)
            self.userInfo(self.token)
            self.taskList(self.token)
            #查询成长值，判断是否升级
            self.userState(self.token, self.upgradeUser, True)
            #self.userCCD(self.token)
            self.getAnswerStatus(self.token)
        except Exception as e:
            logger.error('出错了！', e)

    # 首页模块拆分token
    def getToken(self, redirectUrl):
        # logger.info(f'ccb_gjb redirectUrl : {redirectUrl}')
        #截取token
        token_index = redirectUrl.index('&__dmsp_token=')
        if(token_index>-1):
            i1 = redirectUrl.index('&__dmsp_token=')+len('&__dmsp_token=')
            # logger.info(f'find &__dmsp_token= index : {i1}')
            token = redirectUrl[i1:redirectUrl.index('&', i1)]
            return token
        else:
            return None


    #登录
    def login(self, token):
        url_login = 'https://event.ccbft.com/api/businessCenter/auth/login'
        title = '登录'
        logger.error(f'\n开始{title}')
        url = url_login
        payload = {"token": token,"channelId":"wx"}
        resp = requests.post(url, data= json.dumps(payload), headers = headers)
        if resp.status_code >= 200 and resp.status_code < 300:
            content = resp.content.decode('utf-8')
            # logger.info(content)
            result = json.loads(content, object_hook=customStudentDecoder)
            if(result.success):
                zhc_token = result.data.token
                logger.info(f'登录成功')
                #延时500耗秒
                time.sleep(1)
                self.execCCB(zhc_token)
            else:
                logger.info(f'{title}接口返回错误！')
                logger.info(result)
        else:
            logger.info(f'{title}接口调用失败！{resp.status_code}')
            logger.info(resp.content)


    #查询账户等级信息
    def userState(self, token, callback, notifyFlag = False):
        url_UserState = 'https://event.ccbft.com/api/businessCenter/mainVenue/getUserState'
        title = '查询账户等级信息'
        logger.info(f'\n开始{title}')
        url = url_UserState + '?zhc_token='+token
        resp = requests.post(url, headers = headers)
        if resp.status_code >= 200 and resp.status_code < 300:
            content = resp.content.decode('utf-8')
            result = json.loads(content, object_hook=customStudentDecoder)
            if(result.success):
                logger.info(f'当前账户等级：{result.data.currentLevel},成长值：{result.data.growthExp} / {result.data.nextLevelNeedGrowthExp}')
                logger.info(f'升到下一级还差：{result.data.needGrowthExp}点成长值')
                if(notifyFlag):
                    self.ccbCommon.notify(f'账户等级：{result.data.currentLevel},成长值：{result.data.growthExp} / {result.data.nextLevelNeedGrowthExp}')
                #延时500耗秒
                time.sleep(0.5)
                callback(token, result.data)
                # level = result.data.level
                # rewardId = result.data.zhcRewardInfo.id
                # rewardType = result.data.zhcRewardInfo.rewardType
            else:
                logger.info(f'{title}接口返回错误！')
                logger.info(result)
        else:
            logger.info(f'{title}接口调用失败！{resp.status_code}')
            logger.info(resp.content)

    #获取用户信息
    def getUser(self, token):
        url_getUser='https://event.ccbft.com/api/businessCenter/user/getUser'
        title = '获取用户信息'
        logger.info(f"\n开始{title}")
        url = url_getUser + '?zhc_token='+token
        resp = requests.post(url, data = '{}', headers = headers)
        if resp.status_code >= 200 and resp.status_code < 300:
            content = resp.content.decode('utf-8')
            # logger.info(content)
            result = json.loads(content, object_hook=customStudentDecoder)
            if(result.success):
                #延时500耗秒
                # time.sleep(0.5)
                logger.info(f'当前账户：{result.data.userDTO.userName}')
                self.ccbCommon.notify(f'账户：{result.data.userDTO.userName}')
                self.userName = result.data.userDTO.userName
                self.ccbCommon.userName = result.data.userDTO.userName
                return result.data.userDTO.userId
                # logger.info(result.message)
            else:
                logger.info(f'{title}接口返回错误！')
                logger.info(result)
        else:
            logger.info(f'{title}接口调用失败！{resp.status_code}')
            logger.info(resp.content)
        return None

    #每日领取首页CC币
    def receiveLevelReward(self, token, rewardData):
        url_receiveLevelReward = 'https://event.ccbft.com/api/businessCenter/mainVenue/receiveLevelReward'
        if(rewardData.receiveResult=='00'):
            logger.info('每日首页CC币已领取，跳过！')    
            return
        title = '领取每日首页CC币'
        logger.info(f"\n开始{title}")
        level = rewardData.level
        rewardId = rewardData.zhcRewardInfo.id
        levelRewardType = rewardData.zhcRewardInfo.rewardType
        url = url_receiveLevelReward + '?zhc_token='+token
        payload = {"userId":self.userId,"level":level,"rewardId":rewardId,"levelRewardType":levelRewardType}
        logger.info(f'签到参数：{payload}')
        resp = requests.post(url, data = json.dumps(payload), headers = headers)
        if resp.status_code >= 200 and resp.status_code < 300:
            content = resp.content.decode('utf-8')
            result = json.loads(content, object_hook=customStudentDecoder)
            if(result.success):
                #延时500耗秒
                time.sleep(0.5)
                logger.info(result.message)
            else:
                logger.info(f'{title}接口返回错误！')
                logger.info(result)
        else:
            logger.info(f'{title}接口调用失败！{resp.status_code}')
            logger.info(resp.content)


    #查询账户CC币
    def userCCD(self, token, notifyFlag = False):
        url_UserCCD = 'https://event.ccbft.com/api/businessCenter/user/getUserCCD'
        title = '查询账户CC币'
        logger.info(f"\n开始{title}")
        url = url_UserCCD + '?zhc_token='+token
        resp = requests.post(url, data = '{}', headers = headers)
        if resp.status_code >= 200 and resp.status_code < 300:
            content = resp.content.decode('utf-8')
            result = json.loads(content, object_hook=customStudentDecoder)
            if(result.success):
                #延时500耗秒
                time.sleep(0.5)
                logger.info(f'当前账户cc币：{result.data.userCCBeanInfo.count}')
                logger.info(f'即将过期[{result.data.userCCBeanExpiredInfo.expireDate}]的cc币：{result.data.userCCBeanExpiredInfo.count}')
                if(notifyFlag):
                    self.ccbCommon.notify(f'当前cc币：{result.data.userCCBeanInfo.count}')
                    self.ccbCommon.notify(f'即将过期的cc币：{result.data.userCCBeanExpiredInfo.count}，过期时间：{result.data.userCCBeanExpiredInfo.expireDate}')
                return result.data.userCCBeanInfo.count
            else:
                logger.info(f'{title}接口返回错误！')
                logger.info(result)
        else:
            logger.info(f'{title}接口调用失败！{resp.status_code}')
            logger.info(resp.content)
        return None

    #做成长任务
    def userInfo(self, token):
        url_UserInfo = 'https://event.ccbft.com/api/businessCenter/taskCenter/getUserInfo'
        title = '获取账户信息'
        logger.info(f"\n开始{title}")
        url = url_UserInfo + '?zhc_token='+token
        resp = requests.post(url, data = '{}', headers = headers)
        if resp.status_code >= 200 and resp.status_code < 300:
            content = resp.content.decode('utf-8')
            # logger.info(content)
            result = json.loads(content, object_hook=customStudentDecoder)
            if(result.success):
                isSign = result.data.isSign
                currentDay = result.data.currentDay
                logger.info(f'签到状态：{isSign}, 当前签到天数：{currentDay}')
                taskId = result.data.taskId
                #延时500耗秒
                time.sleep(0.5)
                if(isSign=='00'):
                    self.signin(token, taskId)
                elif(isSign=='01'):
                    logger.info(f'已签到，跳过！')
                else:
                    logger.info(f'签到状态未知？？？')
            else:
                logger.info(f'{title}接口返回错误！')
                logger.info(result)
        else:
            logger.info(f'{title}接口调用失败！{resp.status_code}')
            logger.info(resp.content)


    # 成长值升级
    def upgradeUser(self, token, rewardData):
        url_upgradeUser='https://event.ccbft.com/api/businessCenter/mainVenue/upgradeUser'
        title = '成长值升级'
        logger.info(f"\n开始{title}")
        needGrowthExp = rewardData.needGrowthExp
        logger.info(f"距离下一级还需要{needGrowthExp}点成长值，{'不满足升级条件，跳过升级' if needGrowthExp > 0 else '开始升级！'}")
        if(needGrowthExp > 0):
            return
        url = url_upgradeUser + '?zhc_token='+token
        payload = {'userId':self.userId}
        resp = requests.post(url, data = json.dumps(payload), headers = headers)
        if resp.status_code >= 200 and resp.status_code < 300:
            content = resp.content.decode('utf-8')
            logger.info(content)
            result = json.loads(content, object_hook=customStudentDecoder)
            if(result.success):
                try:
                    logger.info(f'升级成功：{result.data[0].rewardName}')
                except:
                    logger.info(f'升级结果：{result}')
            else:
                logger.info(f'{title}接口返回错误！')
                logger.info(result)
        else:
            logger.info(f'{title}接口调用失败！{resp.status_code}')
            logger.info(resp.content)


    #签到
    def signin(self, token, taskId):
        url_signin = 'https://event.ccbft.com/api/businessCenter/taskCenter/signin'
        title = '签到'
        logger.info(f"\n开始{title}")
        url = url_signin + '?zhc_token='+token
        payload = {'taskId':taskId}
        resp = requests.post(url, data = json.dumps(payload), headers = headers)
        if resp.status_code >= 200 and resp.status_code < 300:
            content = resp.content.decode('utf-8')
            result = json.loads(content, object_hook=customStudentDecoder)
            if(result.success):
                logger.info(result.message)
            else:
                logger.info(f'{title}接口返回错误！')
                logger.info(result)
        else:
            logger.info(f'{title}接口调用失败！{resp.status_code}')
            logger.info(resp.content)


    # 获取日常任务列表
    def taskList(self, token):
        url_TaskList = 'https://event.ccbft.com/api/businessCenter/taskCenter/getTaskList'
        title = '获取日常任务列表'
        logger.info(f"\n开始{title}")
        url = url_TaskList + '?zhc_token='+token
        payload = {'publishChannels':'03','regionId':'110000'}
        resp = requests.post(url, data = json.dumps(payload), headers = headers)
        if resp.status_code >= 200 and resp.status_code < 300:
            content = resp.content.decode('utf-8')
            result = json.loads(content, object_hook=customStudentDecoder)
            if(result.success):
                dayTaskList = result.data.日常任务
                #for dayTask in dayTaskList:
                    #logger.info(f'任务ID：{dayTask.id}, {dayTask.taskName} ,状态：{dayTask.taskDetail.completeStatus}')

                for dayTask in dayTaskList:
                    taskId = dayTask.id
                    if dayTask.taskDetail.completeStatus == '02':
                        logger.info(f'日常任务：{dayTask.taskDetail.completeStatus}，已完成。')
                        continue

                    if dayTask.taskDetail.completeStatus == '01':
                        #延时1000耗秒
                        time.sleep(1)
                        self.receiveReward(token, taskId)
                        continue
                    logger.info(f'开始执行日常任务：{taskId}、{dayTask.taskName}')
                    self.browseTask(token, taskId)
                    #延时1000耗秒
                    time.sleep(1)
                    self.receiveReward(token, taskId)
                    time.sleep(1)
            else:
                logger.info(f'{title}接口返回错误！')
                logger.info(result)
        else:
            logger.info(f'{title}接口调用失败！{resp.status_code}')
            logger.info(resp.content)


    # 点击日常任务
    def browseTask(self, token, taskId):
        url_browseTask = 'https://event.ccbft.com/api/businessCenter/taskCenter/browseTask'
        title = '日常任务'
        #logger.info(f"\n开始{title}")
        url = url_browseTask + '?zhc_token='+token
        payload = {'taskId':taskId,'browseSec':'1'}
        resp = requests.post(url, data = json.dumps(payload), headers = headers)
        if resp.status_code >= 200 and resp.status_code < 300:
            logger.info(f"完成{title}:{taskId}")
        else:
            logger.info(f'{title}接口调用失败！{resp.status_code}')
            logger.info(resp.content)


    # 领取日常任务奖励
    def receiveReward(self, token, taskId):
        url_receiveReward = 'https://event.ccbft.com/api/businessCenter/taskCenter/receiveReward'
        title = '领取日常任务奖励'
        #logger.info(f"\n开始{title}")
        url = url_receiveReward + '?zhc_token='+token
        payload = {'taskId':taskId}
        resp = requests.post(url, data = json.dumps(payload), headers = headers)
        if resp.status_code >= 200 and resp.status_code < 300:
            content = resp.content.decode('utf-8')
            result = json.loads(content, object_hook=customStudentDecoder)
            if(result.success):
                logger.info(result.message)
            else:
                logger.info(f'{title}接口返回错误！')
                logger.info(result)
        else:
            logger.info(f'{title}接口调用失败！{resp.status_code}')
            logger.info(resp.content)


    #获取每日问答是否完成
    def getAnswerStatus(self, token):
        url_getAnswerStatus='https://event.ccbft.com/api/businessCenter/zhcUserDayAnswer/getAnswerStatus'
        title = '获取每日问答是否完成'
        logger.info(f"\n开始{title}")
        url = url_getAnswerStatus + '?zhc_token='+token
        resp = requests.get(url,  headers = headers)
        if resp.status_code >= 200 and resp.status_code < 300:
            content = resp.content.decode('utf-8')
            result = json.loads(content, object_hook=customStudentDecoder)
            if(result.success):
                logger.info(result.message)
                if(result.data.answerState=='N'):
                    self.queryQuestionToday(token)
            else:
                logger.info(f'{title}接口返回错误！')
                logger.info(result)
        else:
            logger.info(f'{title}接口调用失败！{resp.status_code}')
            logger.info(resp.content)


    #每日问答
    def queryQuestionToday(self, token):
        url_queryQuestionToday='https://event.ccbft.com/api/businessCenter/zhcUserDayAnswer/queryQuestionToday'
        title = '获取每日问答题目'
        logger.info(f"\n开始{title}")
        url = url_queryQuestionToday + '?zhc_token='+token
        resp = requests.get(url,  headers = headers)
        if resp.status_code >= 200 and resp.status_code < 300:
            content = resp.content.decode('utf-8')
            result = json.loads(content, object_hook=customStudentDecoder)
            if(result.success):
                questionData = result.data
                questionId = questionData.questionId
                logger.info(f'每日问答：【{questionId}】{questionData.questionName}（{questionData.questionType}）')
                logger.info(f'remark：{questionData.remark}')
                for answer in questionData.answerList:
                    answerId = answer.id
                    logger.info(f'{answer.sort}、【{answerId}】{answer.answerResult}')
                #TODO 答题库...
                questionDB = self.ccbCommon.question.getQuestion(questionId,'每日一答')
                #logger.info(f'获取答题库：{questionDB}')
                
                answerFlag = True
                answerBft =[]
                if(questionDB==None):
                    for answer in questionData.answerList:
                        answerBft.append(answer.id)
                    if(self.ccbCommon.ifSubmitQuestion):
                        self.ccbCommon.question.submitQuestion(questionData, "每日一答")
                else:
                    for answer in questionDB.answerList:
                        if(answer.result == 1):
                            answerFlag = False
                            # logger.info(f'答题： questionId ： {questionId}， options : {answer.id}')
                            self.userAnswerQuestion(token, questionId, answer.id, False)
                            return
                        elif(answer.result == 0):
                            answerBft.append(answer.id)
                if(self.ccbCommon.ifCMDAnswerQuestions):
                        logger.info('----------------限时30秒----------------------')
                        x = -1
                        while x<0 or x > len(questionData.answerList):
                            logger.info('请输入选择的答案序号：')
                            try:
                                x = int(input())
                            except:
                                logger.info(f'请输入数字，且在【1-{len(questionData.answerList)}】范围内！')
                        # logger.info(f'答题： questionId ： {questionId}， options : {options[x-1].id}')
                        self.userAnswerQuestion(token, questionId, questionData.answerList[x-1].id, True)
                else:
                     # answerFlag = True, 表示答题库没有正确答案，需要将提交的结果写入到答题库中
                    # logger.info(f'答题： questionId ： {questionId}， options : {answerBft[0]}')
                    answerIndex = random.randint(0, len(answerBft)-1)
                    self.userAnswerQuestion(token, questionId, answerIndex, True)
            else:
                logger.info(f'{title}接口返回错误！')
                logger.info(result)
        else:
            logger.info(f'{title}接口调用失败！{resp.status_code}')
            logger.info(resp.content)


    #提交每日问答
    def userAnswerQuestion(self, token, questionId, answerId, ifWriteServer):
        url_userAnswerQuestion='https://event.ccbft.com/api/businessCenter/zhcUserDayAnswer/userAnswerQuestion'
        #title = '提交每日问答'
        #logger.info(f"\n开始{title}")
        url = url_userAnswerQuestion + '?zhc_token='+token
        payload = {'questionId':questionId,'answerIds':answerId}
        resp = requests.post(url, data = json.dumps(payload), headers = headers)
        if resp.status_code >= 200 and resp.status_code < 300:
            content = resp.content.decode('utf-8')
            result = json.loads(content, object_hook=customStudentDecoder)
            try:
                for answer in result.data.answerList:
                    if(answer.isCorrect==1):
                        logger.info(f'正确答案是：{answer.answerResult}')
                        logger.info(f'{"回答正确！" if answer.id ==answerId else "回答错误！"}')
                        if(ifWriteServer):
                            logger.info(f'将正确答案上传到答题库！')
                            self.ccbCommon.question.submitQuestionAnswer(answer.questionId, answer.id, 1)
                            logger.info(f'message:{result.message}')
            except Exception as e:
                logger.error(f'{title}接口处理异常！')
        else:
            logger.info(f'{title}接口调用失败！{resp.status_code}')
            logger.info(resp.content)
