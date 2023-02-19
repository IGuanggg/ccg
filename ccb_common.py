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

User_Agent = 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/53.0.2785.116 Safari/537.36 QBCore/4.0.1326.400 QQBrowser/9.0.2524.400 Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/53.0.2875.116 Safari/537.36 NetType/WIFI MicroMessenger/7.0.20.1781(0x6700143B) WindowsWechat(0x63010200)" '
headers = {'content-type': "application/json", 'User-Agent':User_Agent}

# 同上，截取地址的倒数第二个 ？？？
archId = 'ccb_gjb'
# 猜测： cc币注册在微信公众号内的APPID
appId = 'wxd513efdbf26b5744'
# 通过公众号连接，跳转的url（https://event.ccbft.com/e/ccb_gjb/polFsWD2jPnjhOx9ruVBcA?CCB_Chnl=1000102），截取链接最后的地址字符串
shortId = 'polFsWD2jPnjhOx9ruVBcA'


def customStudentDecoder(studentDict):
    return namedtuple('X', studentDict.keys())(*studentDict.values())

class CcbCommon:

    wParamDict = None
    wxUUID = None
    #是否上传每日问答到答题库
    ifSubmitQuestion = True
    #是否尝试随机提交答案，为后续的用户试错
    ifRandomSubmitQuestionAnswer = False
    #是否在命令窗口手动答题
    ifCMDAnswerQuestions = True
    #openCV远程服务接口地址
    opencvUrl = None
    #是否自动抽奖
    autoChou = True
    #街头投篮王
    tlCount = 0

    userId = None
    userName = None
    question = QuestionManager()

    def __init__(self, wParamDict):
        self.wParamDict = wParamDict


    # 配信内容格式 (推送日志)
    allMess = ''
    def notify(self, content=None):
        self.allMess = self.allMess + content + '\n'
        logger.info(content)


    # 通过接口 ：https://event.ccbft.com/api/flow/nf/shortLink/redirect/ccb_gjb?CCB_Chnl=1000102 ，再加上body参数 ccb_gjb_param ，
    # 返回cc币主页跳转地址 redirectUrl，地址上带有token标识
    ccb_gjb_param = {"appId":appId,"shortId":shortId,"archId":archId,"wParam":None,"channelId":"wx","ifWxFirst":True}
    ccb_gjb_param_cache = {"appId":appId,"shortId":shortId,"archId":archId,"wxUUID":None,"channelId":"wx","ifWxFirst":False}

    shelveCache = None
    def getCacheInstance(self, name):
        if(self.shelveCache==None):
            self.shelveCahce = ShelveHelp(name)
        return self.shelveCahce

    def getCache(self, name, key):
        cache = self.getCacheInstance(name)
        obj = cache.read()
        if(obj is not None and obj['code']==1):
            return obj['data'].get(key,None)
        else:
            return None

    def setCache(self, name, key, value):
        cache = self.getCacheInstance(name)
        obj = cache.read()
        if(obj==None):
            obj = {'data':{}}
        obj['data'][key] = value
        cache.write(**obj['data'])

    def getCcbTokenParam(self, name, wParam, ifNotUUID):
        cache = self.getCacheInstance(name)
        obj = cache.read()
        if(ifNotUUID or obj['code']!=1 or obj['data'].get('wxUUID', None)==None or (datetime.now() - obj['data']['wxUUID_Date']).seconds>60*60):
            self.ccb_gjb_param['wParam'] = wParam
            return self.ccb_gjb_param
        else:
            self.ccb_gjb_param_cache['wxUUID'] = obj['data']['wxUUID']
            return self.ccb_gjb_param_cache

    def setCcbTokenParam(self, name, wxUUID):
        cache = self.getCacheInstance(name)
        cache.write(**{'wxUUID':wxUUID,'wxUUID_Date':datetime.now()})

    # 获取token
    def requestToken(self, shortId, chnl = '1000102', ifNotUUID = False, u = None):
        p = f'u={u}' if u is not None else f'CCB_Chnl={chnl}'
        url_ccb_gjb = f'https://event.ccbft.com/api/flow/nf/shortLink/redirect/ccb_gjb?{p}'
        title = '获取token'
        logger.error(f'\n开始{title}')
        url = url_ccb_gjb
        logger.info(url)
        wParamDict = self.wParamDict
        param = self.getCcbTokenParam(wParamDict['name'], wParamDict['wParam'], ifNotUUID)
        param['shortId'] = shortId
        # logger.info(f'param : {json.dumps(param)}')
        redirectResult={}
        resp = requests.post(url, data= json.dumps(param), headers = headers)
        if resp.status_code >= 200 and resp.status_code < 300:
            content = resp.content.decode('utf-8')
            result = json.loads(content, object_hook=customStudentDecoder)
            if(result.success):
                # 使用wParam 获取 redirectUrl
                # logger.info(result)
                if(result.data.wxUUIDExist or result.data.wxUUID is not None):
                    if(result.data.wxUUID is not None):
                        self.wxUUID = result.data.wxUUID
                        self.setCcbTokenParam(wParamDict['name'], self.wxUUID)
                # 使用wxUUID 获取 redirectUrl
                elif param['wxUUID'] is not None and (not result.data.wxUUIDExist):
                    self.setCcbTokenParam(wParamDict['name'], None)
                    return self.requestToken(shortId, chnl, True)
                else:
                    logger.info('获取Token失败！')
                    logger.info(result)
                redirectResult['redirectUrl']=result.data.redirectUrl
                redirectResult['cookie']=resp.cookies
                return redirectResult
            else:
                logger.info(f'{title}接口返回错误！')
                logger.info(result)
                return redirectResult
        else:
            logger.info(f'{title}接口调用失败！{resp.status_code}')
            logger.info(resp.content)
            return redirectResult      


    #抓取网页的cookie 和 页面定义的js参数
    def captureWebCK(self, url, cookie, title):
        logger.info(f"\n开始{title}")
        webResult = {}
        resp = requests.get(url, allow_redirects=True, headers=headers)
        if(resp.ok):
            h = resp.history[len(resp.history)-1]
            webResult['cookie']=resp.cookies
            # logger.info(f'cookie:{resp.cookies}')
            webResult['url']=h.headers['location']
            # logger.info(f'302跳转后服务器地址：{webResult["url"]}')
            # for i,h in enumerate(resp.history):
            #    logger.info(f'重定向 {i}：\n{h.url}')
            #    logger.info(f'cookie:{resp.cookies}')
            # if(resp.status_code==302):
            content = resp.content.decode('utf-8')
            mateHeader ='<meta name=csrf-token content="'
            csrfTokenIndex1 = content.find(mateHeader)+len(mateHeader)
            csrfTokenIndex2 = content.find('"', csrfTokenIndex1)
            csrfToken = content[csrfTokenIndex1:csrfTokenIndex2]
            webResult['csrfToken']=csrfToken
        #     logger.info(f'跳转后的url：{refreshUrl}')
        #     resp2 = requests.get(refreshUrl, headers=headers)
        #     webResult['cookie']=resp2.cookies
        #     return webResult
        return webResult


    #缓存助力码 shareData = {'yldk':'123456','kjzq':'654321',...}
    def cacheShareData(self, shareCode, shareType):
        if(self.userId is None):
            logger.error(f'缓存助力码失败，userId为空。????????????')
            return
        value = self.getCache('common', 'share')
        # logger.info(f'缓存的助力码：{value}')
        if(value is None):
            value = []
        for v in value:
            #已存在，无需缓存
            if(self.userId == v.get('userId','')):
                hasRefresh = False
                if(not 'userName' in v or v.get('userName',None)!=self.userName):
                    hasRefresh = True
                    v['userName'] = self.userName
                if(not shareType in v.get('shareData') or v.get('shareData').get(shareType,None) != shareCode):
                    hasRefresh = True
                    v['shareData'][shareType] = shareCode
                if(hasRefresh):
                    self.setCache('common', 'share', value)
                return
        #新加入的用户 ，追加到最后面
        value.append({'userId':self.userId,'userName':self.userName,'shareData':{shareType:shareCode}})
        self.setCache('common', 'share', value)


    def getShareData(self, shareType):
        value = self.getCache('common', 'share')
        if(value is None):
            value = []
        # 定位到自己的ID，然后获取下一个可以助力的账户
        currentIndex = -1
        clearShareData=[]
        for i,v in enumerate(value):
            id = v.get('userId',None)
            if(id is None):
                clearShareData.append(v)
            elif(self.userId == id):
                currentIndex = i
        if len(clearShareData)>0:
            for d in clearShareData:
                value.remove(d)
            self.setCache('common', 'share', value)
        if(currentIndex==-1):
            value.append({'userId':self.userId,'userName':self.userName,'shareData':{}})
            self.setCache('common', 'share', value)
            currentIndex = len(value)-1
        # 获取助力码规则： 取助力码缓存队列中，排在自己的前一位
        if(len(value)==1):
            return None
        startIndex = currentIndex-1 if(currentIndex-1>=0) else len(value)-1
        shareData =value[startIndex]['shareData'].get(shareType, None) if (shareType in value[startIndex]['shareData']) else None
        userName = value[startIndex].get('userName',None) if ('userName' in value[startIndex]) else None
        logger.info(f'获取到【{userName}】{shareType}助力码：{shareData}')
        return shareData