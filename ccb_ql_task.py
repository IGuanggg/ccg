
from ccb_common import CcbCommon
from ccb_home import CcbHome
from ccb_yldk import CcbYldk
from ccb_ylyl import CcbYlyl
from ccb_kjzq import CcbKjzq
from ccb_shzq import CcbShzq
from ccb_xbzsdky import CcbXbzsdky
from ccb_fsj import CcbFsj
from ccb_xbnndcg import CcbXbnndcg
from ccb_xbptdzz import CcbXbptdzz
from ccb_gfsyjf import CcbGfsyjf
from ccb_jttlw import CcbJttlw
import time
import os
import logging
import logging.handlers
import datetime

# 日志模块
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logFormat = logging.Formatter("%(message)s")

# 日志输出流
stream = logging.StreamHandler()
stream.setFormatter(logFormat)
logger.addHandler(stream)

# 配信文件
try:
    from sendNotify import send
except Exception as error:
    logger.info('推送文件有误')
    logger.info(f'失败原因:{error}')

def env(key):
    return os.environ.get(key)

def getwParam():
    ccb = env('CCB_COOKIE')
    ccbList = ccb.split("&")
    wParamList = []
    for c in ccbList:
        v = c.split(";")
        name = v[0]
        value = v[1]
        wParamList.append({'name':name,'wParam':value})
    return wParamList



# 早上5-9点执行，养老打卡

def exec(common,wParam):
    #是否在命令窗口手动答题
    common.ifCMDAnswerQuestions = False
    #是否自动抽奖，默认：true
    autoChou = False
    if env('CCB_AUTO_CHOU') == '1':
        autoChou = True;
    common.autoChou = autoChou;
    # 街头投篮王 游戏次数
    tlCount = 0
    try:
        if env('CCB_TOULAN') is not None:
            tlCount = int(env('CCB_TOULAN'));
    except Exception as e:
        logger.error('环境变量CCB_TOULAN设定有误！')
    common.tlCount = tlCount;
    common.opencvUrl = env('CCB_OPENCV_URL')
    #首页
    home = CcbHome(common)
    home.exec()
    # #养老打卡
    yldk = CcbYldk(common)
    yldk.exec()
    common.notify(f'养老打卡：{"#异常" if yldk.runStatus is None else ("√" if yldk.runStatus else "x")}')
    # #裕龙有礼
    ylyl = CcbYlyl(common)
    ylyl.exec()
    common.notify(f'裕龙有礼：{"#异常" if not ylyl.runStatus else (f"刮卡{ylyl.runCount}次")} ')

    #跨境专区（答题）
    kjzq = CcbKjzq(common)
    kjzq.exec()
    common.notify(f'跨境专区：{"#异常" if not kjzq.runStatus else (f"答题{kjzq.runCount}次，抽奖{kjzq.drawCount}次")} ')
    
    #商户专区
    shzq = CcbShzq(common)
    shzq.exec()
    common.notify(f'商户专区：{"#异常" if not shzq.runStatus else (f"掷骰子{shzq.drawCount}次")} ')
    
    #消保知识大考验（答题）
    xbzsdky = CcbXbzsdky(common)
    xbzsdky.exec()
    common.notify(f'消保知识大考验：{"#异常" if not xbzsdky.runStatus else (f"答题{xbzsdky.runCount}次，抽奖{xbzsdky.drawCount}次")} ')
    
    # 丰收节
    fsj = CcbFsj(common)
    fsj.exec()
    common.notify(f'丰收节：{"#异常" if not fsj.runStatus else (f"掷骰子{fsj.drawCount}次")} ')
    
    # 消保拼图大作战
    xbptdzz = CcbXbptdzz(common)
    xbptdzz.exec()
    common.notify(f'消保拼图大作战：{"#异常" if not xbptdzz.runStatus else (f"拼图{xbptdzz.runCount}次，抽奖{xbptdzz.drawCount}次")} ')

    # 消保牛牛闯关
    xbnndcg = CcbXbnndcg(common)
    xbnndcg.exec()
    common.notify(f'消保牛牛闯关：{"#异常" if not xbnndcg.runStatus else (f"答题{xbnndcg.runCount}次，抽奖{xbnndcg.drawCount}次")} ')

    #瓜分十亿积分
    gfsyjf = CcbGfsyjf(common)
    gfsyjf.exec()
    common.notify(f'瓜分十亿积分：{"#异常" if not gfsyjf.runStatus else (f"抽卡{gfsyjf.drawCount}次")} ')
    common.notify(f'    卡牌数量：{gfsyjf.log}')

    #街头投篮王
    if(common.tlCount>0):
        jttlw = CcbJttlw(common)
        jttlw.exec()
        ticketCcb = jttlw.runCount*jttlw.ticket
        jWin = jttlw.runGot - ticketCcb
        common.notify(f'街头投篮王：{"#异常" if not jttlw.runStatus else (f"玩{jttlw.runCount}局,共赢得{jttlw.runGot}豆,支出门票{ticketCcb}豆,结余{jWin}豆。")} ')


    #最后查询账户ccb, 用于推送通知
    endCcbCount = home.userCCD(home.token, True)
    if(home.initCcbCount is not None and endCcbCount is not None):
        toDayCcbCount = endCcbCount - home.initCcbCount
        common.notify(f'本次运行共收入：{toDayCcbCount}CCB')

    

if __name__ == '__main__':
    stop_time = '2022-12-31'
    currentTime = datetime.datetime.now().strftime('%Y-%m-%d')
    if(currentTime < stop_time):
        wParamList = getwParam()
        logger.info(f'检测到{len(wParamList)}个账号')
        for index,wParam in enumerate(wParamList):
            logger.info(f'\n=======开始执行【{wParam["name"]}】======')
            try:
                common = CcbCommon(wParam)
                exec(common, wParam)
                send('建行ccb',common.allMess)
            except Exception as e:
                logger.error('出错了，切换下一个账号！', e)
            logger.info('等待20秒后切换下一个账号')
            time.sleep(20)
    else:
        send('建行ccb', '活动已结束, bye!')  