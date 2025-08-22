import os
import glob
import time
import sys
import json
import threading
from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.request import CommonRequest

import nls

URL="wss://nls-gateway-cn-shanghai.aliyuncs.com/ws/v1"
# 于下面获取
token = "yourToken"       #参考https://help.aliyun.com/document_detail/450255.html获取token
APPKEY="yourAppkey"       #获取Appkey请前往控制台：https://nls-portal.console.aliyun.com/applist

# 下面获取token
# 创建AcsClient实例
client = AcsClient(
   os.getenv('ALIYUN_AK_ID'),
   os.getenv('ALIYUN_AK_SECRET'),
   "cn-shanghai"
);

# 创建request，并设置参数。
request = CommonRequest()
request.set_method('POST')
request.set_domain('nls-meta.cn-shanghai.aliyuncs.com')
request.set_version('2019-02-28')
request.set_action_name('CreateToken')

try : 
    response = client.do_action_with_exception(request)
    print(response)

    jss = json.loads(response)
    if 'Token' in jss and 'Id' in jss['Token']:
        # 得到token
        token = jss['Token']['Id']
        expireTime = jss['Token']['ExpireTime']
        print("token = " + token)
        print("expireTime = " + str(expireTime))

except Exception as e:
   print(e)

# 定义最大可用线程数量
THREAD_COUNT_MAX = 5
thread_id_pool = list(range(THREAD_COUNT_MAX))
thread_lock = threading.Lock()

TEXTs = ['大壮正想去摘取花瓣，谁知阿丽和阿强突然内讧，阿丽拿去手枪向树干边的阿强射击，两声枪响，阿强直接倒入水中',
         '大壮觉得很抱歉，不该在阿丽和阿强内讧时摘取花瓣，但是阿丽并没有责怪他，阿强从水中站起来也说没有关系',
         '阿强转身对阿丽说，下次请不要用空包弹，太吓人了，要杀我，其实不需要使用手枪，你一早就做到了',
         '阿丽气呼呼地说，我再也不要见到你们俩人了，随手利落地拆下弹夹，清空弹仓，把手枪插回裙子里，转身就走了',
         '大壮和阿强望着阿丽的背影，一时无语，大壮率先打破了静默说，我们去喝一杯吗？阿强点头表示同意']

#以下代码会根据上述TEXT文本反复进行语音合成
class TestTts:
    def __init__(self, tid, test_file):
        self.__th = threading.Thread(target=self.__test_run)
        self.__tid = tid
        self.__id = "thread" + str(tid)
        self.__test_file = test_file
   
    def start(self, text):
        self.__text = text
        self.__f = open(self.__test_file, "wb")
        self.__th.start()
    
    def test_on_metainfo(self, message, *args):
        print("on_metainfo message=>{}".format(message))  

    def test_on_error(self, message, *args):
        print("on_error args=>{}".format(args))

    def test_on_close(self, *args):
        print("on_close: args=>{}".format(args))
        try:
            self.__f.close()
        except Exception as e:
            print("close file failed since:", e)
        # 释放可用Thread Id
        with thread_lock:
            thread_id_pool.append(self.__tid)

    def test_on_data(self, data, *args):
        try:
            self.__f.write(data)
        except Exception as e:
            print("write data failed:", e)

    def test_on_completed(self, message, *args):
        print("on_completed:args=>{} message=>{}".format(args, message))


    def __test_run(self):
      	print("thread:{} start..".format(self.__id))
      	tts = nls.NlsSpeechSynthesizer(url=URL,
      	      	      	      	       token=token,
      	      	      	      	       appkey=APPKEY,
      	      	      	      	       on_metainfo=self.test_on_metainfo,
      	      	      	      	       on_data=self.test_on_data,
      	      	      	      	       on_completed=self.test_on_completed,
      	      	      	      	       on_error=self.test_on_error,
      	      	      	      	       on_close=self.test_on_close,
      	      	      	      	       callback_args=[self.__id])
      	print("{}: session start".format(self.__id))
      	r = tts.start(self.__text, voice="Stanley", aformat="wav", sample_rate=48000, speech_rate=-140)
      	print("{}: tts done with result:{}".format(self.__id, r))

def multiruntest(thread_id, input_text, output_path):
    t = TestTts(thread_id, output_path)
    t.start(input_text)

nls.enableTrace(True)

output_wav_path = "./test"

if os.path.isdir(output_wav_path):
    # 清理旧wav文件
    clear_path = output_wav_path + "/" + "*.wav"
    files = glob.glob(clear_path)
    for f in files:
        os.remove(f)
else:
    # 创建生成wav文件目录
    os.mkdir(output_wav_path)

file_id = 0
for text in TEXTs:
    wav_name = f"{file_id:05}.wav"
    output_path = output_wav_path + "/" + wav_name
    # 仅使用可用数量的Thread
    thread_id = -1
    while thread_id == -1:
        with thread_lock:
            if len(thread_id_pool) > 0:
                thread_id = thread_id_pool.pop()
        time.sleep(2)
        
    
    if thread_id != -1:
        # 生成wav
        multiruntest(thread_id, text, output_path)

    file_id += 1
