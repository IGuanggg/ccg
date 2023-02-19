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

#消保拼图大作战
shortId_xbptdzz = 'vqNtoSzskOZCkfLleN5DMQ'

class CcbXbptdzz:
      
    ccbCommon = None

    #答题、抽奖次数
    runCount = 0
    drawCount = 0
    runStatus = True

    def __init__(self, ccbCommon):
        self.ccbCommon = ccbCommon

    def exec(self):
        #消保拼图大作战
        try:
            shareCode = self.ccbCommon.getShareData('xbptdzz')
            redirectResult = self.ccbCommon.requestToken(shortId_xbptdzz, '1000102',u=shareCode)
            redirectUrl = redirectResult['redirectUrl']
            redirectCookie = redirectResult['cookie']
            xbptdzzResult = self.ccbCommon.captureWebCK(redirectUrl, redirectCookie, '抓取消保拼图大作战参数')
            xbptdzz_cookie = xbptdzzResult['cookie']
            xbptdzz_url = xbptdzzResult['url']
            xbptdzz_domain = xbptdzz_url[0:xbptdzz_url.find('/',xbptdzz_url.find('://')+3)]
            xbptdzz_csrfToken = xbptdzzResult['csrfToken']
            self.getShareCode(xbptdzz_domain ,xbptdzz_cookie)
            #使用opencv远程服务接口
            if(self.ccbCommon.opencvUrl is None or len(self.ccbCommon.opencvUrl)==0):
                logger.error('没有检测到可用的openCV远程服务接口，无法参与拼图大作战活动！')   
                return
            #测试远程服务接口状态，
            opencvStatus = self.ccbCommon.question.opencvServerState(self.ccbCommon.opencvUrl)
            if(not opencvStatus):
                logger.error('没有检测到可用的openCV远程服务接口，无法参与拼图大作战活动！')   
                return
            #获取拼图
            self.xbptdzzUserData(xbptdzz_domain, xbptdzz_cookie, xbptdzz_csrfToken)
        except Exception as e:
            self.runStatus = False
            logger.error('出错了！', e)

    def xbptdzzUserData(self, xbptdzz_domain, cookie, csrfToken):
        url_xbptdzz_userData=f'{xbptdzz_domain}/activity/dmspjigsaw/userData/224/zZ6NlyZk'
        title = '查询消保拼图大作战活动次数'
        logger.info(f"\n开始{title}")
        url = url_xbptdzz_userData
        # payload = {'sort':ptSort}
        headers = {'User-Agent':User_Agent, 'X-CSRF-TOKEN':csrfToken}
        resp = requests.get(url, headers = headers, cookies=cookie)
        if resp.status_code >= 200 and resp.status_code < 300:
            content = resp.content.decode('utf-8')
            # logger.info(content)
            result = json.loads(content, object_hook=customStudentDecoder)
            if(result.status=='success'):
                #今日剩余活动次数
                remain_num = int(result.data.remain_num)
                #抽奖次数
                draw_remain_num = int(result.data.draw_remain_num)
                logger.info(f'剩余拼图次数：{remain_num}， 抽奖次数:{draw_remain_num}')
                if(remain_num>0):
                    logger.info('延时3秒')
                    time.sleep(3)
                    self.sbptdzzStart(xbptdzz_domain, cookie, csrfToken)
                elif(draw_remain_num>0):
                    #抽奖
                    if(self.ccbCommon.autoChou):
                        while(draw_remain_num>0):
                            draw_remain_num-=1
                            logger.info('延时8秒')
                            time.sleep(8)
                            self.xbptdzzDrawPrize(xbptdzz_domain, cookie, csrfToken)
            else:
                logger.info(f'{title}接口返回错误！')
                logger.info(result)
        else:
            logger.info(f'{title}接口调用失败！{resp.status_code}')
            logger.info(resp.content)


    #开始游戏 消保拼图大作战
    def sbptdzzStart(self, xbptdzz_domain, cookie, csrfToken):
        url_xbptdzz_start=f'{xbptdzz_domain}/activity/dmspjigsaw/jigsawStart/224/zZ6NlyZk'  
        title = '游戏-消保拼图大作战'      
        logger.info(f"\n开始{title}")
        url = url_xbptdzz_start
        headers = {'content-type': "application/json",'User-Agent':User_Agent, 'X-CSRF-TOKEN':csrfToken}
        resp = requests.post(url, data = '',headers = headers, cookies=cookie)
        if resp.status_code >= 200 and resp.status_code < 300:
            self.runCount+=1
            content = resp.content.decode('utf-8')
            # logger.info(content)
            result = json.loads(content, object_hook=customStudentDecoder)
            # logger.info(result)
            if(result.status=='success'):
                logger.info('延时10秒')
                time.sleep(10)
                self.xbptdzzImage(xbptdzz_domain, cookie, csrfToken)
            else:
                logger.info(f'{title}接口返回错误！')
                logger.info(result)
        else:
            logger.info(f'{title}接口调用失败！{resp.status_code}')
            logger.info(resp.content)

    #消保拼图大作战 - 拼图
    def xbptdzzImage(self, xbptdzz_domain, cookie, csrfToken):
        url_xbptdzz_img=f'{xbptdzz_domain}/activity/dmspjigsaw/getJigsawImgs/224/zZ6NlyZk'
        title = '获取消保拼图大作战的拼图数据'
        logger.info(f"\n开始{title}")
        url = url_xbptdzz_img
        headers = {'content-type': "application/json",'User-Agent':User_Agent, 'X-CSRF-TOKEN':csrfToken}
        resp = requests.post(url, data = '',headers = headers, cookies=cookie)
        if resp.status_code >= 200 and resp.status_code < 300:
            content = resp.content.decode('utf-8')
            # logger.info(content)
            result = json.loads(content, object_hook=customStudentDecoder)
            # logger.info(result)
            if(result.status=='success'):
                nResult = self.ccbCommon.question.requestOpenCV(self.ccbCommon.opencvUrl, content)
                if(nResult is not None):
                    logger.info(f'拼图识别, 顺序：{nResult}')
                    logger.info('延时8秒')
                    time.sleep(8)
                    self.xbptdzzDo(xbptdzz_domain, cookie, nResult, csrfToken)
                else:
                    logger.info('拼图服务接口识图失败了。。。')
            else:
                logger.info(f'{title}接口返回错误！')
                logger.info(result)
        else:
            logger.info(f'{title}接口调用失败！{resp.status_code}')
            logger.info(resp.content)


    #消保拼图大作战 - 提交答案
    def xbptdzzDo(self, xbptdzz_domain, cookie, ptSort, csrfToken):
        url_xbptdzz_do=f'{xbptdzz_domain}/activity/dmspjigsaw/checkJigsaw/224/zZ6NlyZk'
        title = '提交消保拼图大作战拼图答案'
        logger.info(f"\n开始{title}")
        url = url_xbptdzz_do
        payload = {'sort':ptSort}
        headers = {'content-type': "application/json", 'User-Agent':User_Agent, 'X-CSRF-TOKEN':csrfToken}
        resp = requests.post(url, data = json.dumps(payload), headers = headers, cookies=cookie)
        if resp.status_code >= 200 and resp.status_code < 300:
            content = resp.content.decode('utf-8')
            # logger.info(content)
            result = json.loads(content, object_hook=customStudentDecoder)
            if(result.status=='success'):
                pt_status = result.data.status
                logger.info(f'拼图{"正确！" if(pt_status==1) else "错误。。。"}')
                #今日剩余活动次数
                remain_num = int(result.data.remain_num)
                logger.info(f'剩余拼图次数：{remain_num}， status:{pt_status}')
                if(remain_num>0):
                    logger.info('延时3秒')
                    time.sleep(3)
                    self.sbptdzzStart(xbptdzz_domain, cookie, csrfToken)
                else:
                    logger.info('延时2秒')
                    time.sleep(2)
                    self.xbptdzzUserData(xbptdzz_domain, cookie, csrfToken)
            else:
                logger.info(f'{title}接口返回错误！')
                logger.info(result)
        else:
            logger.info(f'{title}接口调用失败！{resp.status_code}')
            logger.info(resp.content)


    #消保拼图大作战 - 抽奖
    def xbptdzzDrawPrize(self, xbptdzz_domain, cookie, csrfToken):
        url_xbptdzz_commonDrawPrize=f'{xbptdzz_domain}/Component/draw/commonDrawPrize/224/zZ6NlyZk'
        title = '消保拼图大作战抽奖'
        logger.info(f"\n开始{title}")
        url = url_xbptdzz_commonDrawPrize
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


    # 获取消保拼图大作战助力码
    def getShareCode(self, xbptdzz_domain, cookie):
        url_xbptdzz_userInfo=f'{xbptdzz_domain}/Common/activity/getUserInfo/224/zZ6NlyZk'
        title = '获取消保拼图大作战助力码'
        logger.info(f"\n开始{title}")
        url = url_xbptdzz_userInfo
        headers = {'User-Agent':User_Agent}
        resp = requests.get(url, headers = headers, cookies=cookie)
        if resp.status_code >= 200 and resp.status_code < 300:
            content = resp.content.decode('utf-8')
            # logger.info(content)
            result = json.loads(content, object_hook=customStudentDecoder)
            if(result.status=='success'):
                shareCode = result.data.ident
                # logger.info(f'助力码：{shareCode}')
                self.ccbCommon.cacheShareData(shareCode, 'xbptdzz')
            else:
                logger.info(f'{title}接口返回错误！')
                logger.info(result)
        else:
            logger.info(f'{title}接口调用失败！{resp.status_code}')
            logger.info(resp.content)


# if __name__=='__main__':
#     content = '''{"status":"success","code":"","message":"ok","data":{"thumb":{"N0":"https://ccbhdimg.kerlala.com/hd/users/10579/20220413/5178111913.png","N1":"https://ccbhdimg.kerlala.com/hd/users/10579/20220413/3996641913.png","N2":"https://ccbhdimg.kerlala.com/hd/users/10579/20220413/2499681913.png","N3":"https://ccbhdimg.kerlala.com/hd/users/10579/20220413/8474911913.png","N4":"https://ccbhdimg.kerlala.com/hd/users/10579/20220413/7613731913.png","N5":"https://ccbhdimg.kerlala.com/hd/users/10579/20220413/3398981913.png","N6":"https://ccbhdimg.kerlala.com/hd/users/10579/20220413/7722531913.png","N7":"https://ccbhdimg.kerlala.com/hd/users/10579/20220413/3025741913.png","N8":"https://ccbhdimg.kerlala.com/hd/users/10579/20220413/9680191913.png"},"img":"https://ccbhdimg.kerlala.com/hd/users/10579/20220413/8174421913.png"}}'''
#     result = json.loads(content, object_hook=customStudentDecoder)
#     if(result.status=='success'):
    #     img = result.data.img
    #     thumb = result.data.thumb._asdict()
    #     ptImgs =[]
    #     for n in thumb.keys():
    #         ptImgs.append({'n':n,'url':thumb.get(n)})
    #     ptdzz.loadImage(ptImgs)
    #     largeImg = ptdzz.readImage(img)
    #     ptdzz.ptImage(largeImg, ptImgs)
    # w = ptImgs[0]['width']
    # h = ptImgs[0]['height']
    # rowSpan = 3
    # rowNum = 0
    # colNum = 0
    # restore_image = np.zeros([rowSpan*h, rowSpan*w, rowSpan], np.uint8)
    # for i,p in enumerate(ptImgs):
    #     MPx,MPy = p['loc']
    #     rowNum = i%rowSpan
    #     colNum = i//rowSpan
    # print(MPx, MPy, f'n:{p["n"]}, row:{rowNum}, col:{colNum}')
    #     restore_image[colNum*h:(colNum+1)*h,rowNum*w:(rowNum+1)*w]=p['img']
    # cv2.imshow('restore_image',restore_image)
    # cv2.waitKey(0)