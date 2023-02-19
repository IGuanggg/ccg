import requests
import json
import time
from collections import namedtuple

def customStudentDecoder(studentDict):
    return namedtuple('X', studentDict.keys())(*studentDict.values())

class QuestionManager:

    url_domain = 'http://43.143.30.70:5000'
    #url_domain = 'http://127.0.0.1:5000'
    url_question = f'{url_domain}/ccb/question'


    def getQuestion(self, id, type):
        title = '查询答题库（每日一题）'
        url = f'{self.url_question}/{id}?type={type}'
        resp = requests.get(url)
        if(resp.ok):
            content = resp.content.decode('utf-8')
            result = json.loads(content, object_hook=customStudentDecoder)
            if(result.code == 1):
                return result.data
            else:
                print(f'{title}失败，{result.msg}')
                return None
        else:
            print(f'{title}接口调用失败！{resp.status_code}')
            print(resp.content)
            return redirectResult
        return None
    
    def getQuestionName(self, name, type):
        title = '查询答题库'
        url = f'{self.url_question}/search'
        payload={'questionName':name, 'type':type}
        resp = requests.post(url, data=json.dumps(payload), headers = {'content-type': "application/json"})
        if(resp.ok):
            content = resp.content.decode('utf-8')
            result = json.loads(content, object_hook=customStudentDecoder)
            if(result.code == 1):
                return result.data
            else:
                print(f'{title}失败，{result.msg}')
                return None
        else:
            print(f'{title}接口调用失败！{resp.status_code}')
            print(resp.content)
            return redirectResult
        return None
    
    
    def submitQuestion(self, data, type, answerId=0, anResult=0):
        title = f'提交答题库（{type}）'
        url = self.url_question
        payload = self.getQuestionData(data, type, answerId, anResult)
        # print(json.dumps(payload))
        resp = requests.post(url, data=json.dumps(payload), headers = {'content-type': "application/json"})
        if(resp.ok):
            content = resp.content.decode('utf-8')
            result = json.loads(content, object_hook=customStudentDecoder)
            if(result.code == 1):
                return True
            else:
                print(content)
                print(payload)
                print(f'answerId = {answerId} , anResult = {anResult}')
                print(f'{title}失败，{result.msg}')
                return False
        else:
            print(f'{title}接口调用失败！{resp.status_code}')
            print(resp.content)
            return False
        return False


    def submitQuestionAnswer(self, questionId, answerId, anResult):
        title = '提交答题库答案（每日一题）'
        url = self.url_question
        payload= {'questionId':questionId, 'id': answerId, 'result': anResult}
        resp = requests.put(url, data=json.dumps(payload), headers = {'content-type': "application/json"})
        if(resp.ok):
            content = resp.content.decode('utf-8')
            result = json.loads(content, object_hook=customStudentDecoder)
            if(result.code == 1):
                return True
            else:
                print(content)
                print(payload)
                print(f'answerId = {answerId} , anResult = {anResult}')
                print(f'{title}失败，{result.msg}')
                return False
        else:
            print(f'{title}接口调用失败！{resp.status_code}')
            print(resp.content)
            return redirectResult
        return False

    def getQuestionData(self,data, type, answerId, anResult):
        if(type=='每日一答'):
            question = {'questionId':data.questionId, 'questionName': data.questionName, 'questionType': data.questionType, 'remark': data.remark, 'type':type}
            answerData = []
            for answer in data.answerList:
                id = answer.id
                questionId = answer.questionId
                answerResult = answer.answerResult
                sort = answer.sort
                r = anResult if(id == answerId) else 0
                answerData.append({'id':id, 'questionId':questionId, 'answerResult':answerResult, 'sort':sort, 'result':r})
            return {'question': question, 'answer': answerData}
        elif(type=='跨境专区' or type=='消保知识大考验'):
            questionId = data.questionId
            question = {'questionId':questionId, 'questionName': data.title, 'questionType': data.type, 'remark': '', 'type':type}
            answerData = []
            for n ,answer in enumerate(data.options):
                id = answer.id
                questionId = questionId
                answerResult = answer.option
                sort = n
                r = anResult if(id == answerId) else 0
                answerData.append({'id':id, 'questionId':questionId, 'answerResult':answerResult, 'sort':sort, 'result':r})
            return {'question': question, 'answer': answerData}
        elif(type=='消保牛牛大闯关'):
            # questionId = f'{data.boutId}_{data.level}_{data.question_no}'
            questionId = data.start_time
            question = {'questionId':questionId, 'questionName': data.title, 'questionType': data.type, 'remark': '', 'type':type}
            answerData = []
            for n ,answer in enumerate(data.options):
                id = answer.id
                questionId = questionId
                answerResult = answer.title
                sort = n
                r = anResult if(id == answerId) else 0
                answerData.append({'id':id, 'questionId':questionId, 'answerResult':answerResult, 'sort':sort, 'result':r})
            return {'question': question, 'answer': answerData}

    def opencvServerState(self, url):
        try:
            title = '拼图服务接口状态'
            print(f'开始测试{title}')
            resp = requests.post(f'{url}/ccb/status', timeout=(3.05,10))
            if(resp.ok):
                content = resp.content.decode('utf-8')
                result = json.loads(content, object_hook=customStudentDecoder)
                if(result.code == 200):
                    print(f'{title}正常！')
                    return True
        except Exception as e:
            print(e)
        print(f'{title}异常!')
        return False

    def requestOpenCV(self, url, data):    
        try:
            title = '拼图服务接口'
            #print(f'开始请求{title}')
            headers = {'content-type': "application/json"}
            resp = requests.post(f'{url}/ccb/jigsaw', data= data, timeout=(3.05,10), headers=headers)
            if(resp.ok):
                content = resp.content.decode('utf-8')
                result = json.loads(content, object_hook=customStudentDecoder)
                if(result.code == 200):
                    return result.data
        except Exception as e:
            print(e)
        print(f'{title}异常!')
        return None

    def testOpenCV(self, url):
        content = '''{"status":"success","code":"","message":"ok","data":{"thumb":{"N0":"https://ccbhdimg.kerlala.com/hd/users/10579/20220413/5178111913.png","N1":"https://ccbhdimg.kerlala.com/hd/users/10579/20220413/3996641913.png","N2":"https://ccbhdimg.kerlala.com/hd/users/10579/20220413/2499681913.png","N3":"https://ccbhdimg.kerlala.com/hd/users/10579/20220413/8474911913.png","N4":"https://ccbhdimg.kerlala.com/hd/users/10579/20220413/7613731913.png","N5":"https://ccbhdimg.kerlala.com/hd/users/10579/20220413/3398981913.png","N6":"https://ccbhdimg.kerlala.com/hd/users/10579/20220413/7722531913.png","N7":"https://ccbhdimg.kerlala.com/hd/users/10579/20220413/3025741913.png","N8":"https://ccbhdimg.kerlala.com/hd/users/10579/20220413/9680191913.png"},"img":"https://ccbhdimg.kerlala.com/hd/users/10579/20220413/8174421913.png"}}'''
        result = json.loads(content, object_hook=customStudentDecoder)
        if(result.status=='success'):
            nResult = qm.requestOpenCV(opencvUrl, content)
            print(nResult)
            #print('测试拼图服务接口状态：正常')
        else:
            print('测试拼图服务接口状态：异常')

if __name__=='__main__':
    qm = QuestionManager()
    # question = qm.getQuestion(28)
    # print(question)
    opencvUrl = 'http://127.0.0.1:8998'
    qm.testOpenCV(opencvUrl)
    