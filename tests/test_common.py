import time
import threading
import sys

import nls

URL="wss://nls-gateway.cn-shanghai.aliyuncs.com/ws/v1"
AKID="Your AKID"
AKKEY="Your AKSECRET"
APPKEY="Your APPKEY"

class TestSrCommon:
    def __init__(self, tid, test_file):
        self.__th = threading.Thread(target=self.__test_run)
        self.__id = tid
        self.__test_file = test_file
   
    def loadfile(self, filename):
        with open(filename, "rb") as f:
            self.__data = f.read()
    
    def start(self):
        self.loadfile(self.__test_file)
        self.__th.start()

    def test_on_open(self, *args):
        print("test_on_start")

    def test_on_start(self, message, *args):
        print("test_on_start:{}".format(message))

    def test_on_data(self, data, *args):
        pass

    def test_on_error(self, message, *args):
        print("on_error args=>{}".format(args))

    def test_on_close(self, *args):
        print("on_close: args=>{}".format(args))

    def test_on_result_chg(self, message, *args):
        print("test_on_chg:{}".format(message))

    def test_on_completed(self, message, *args):
        print("on_completed:args=>{} message=>{}".format(args, message))
        self.__sr.shutdown() 

    def __test_run(self):
        print("thread:{} start..".format(self.__id))
        callbacks = {
                "RecognitionStarted":self.test_on_start,
                "RecognitionResultChanged":self.test_on_result_chg,
                "RecognitionCompleted":self.test_on_completed
                }
        self.__sr = nls.NlsCommonProto(
                    url=URL,
                    akid=AKID,
                    aksecret=AKKEY,
                    appkey=APPKEY,
                    namespace="SpeechRecognizer",
                    on_open=self.test_on_open,
                    on_data=self.test_on_data,
                    on_error=self.test_on_error,
                    on_close=self.test_on_close,
                    user_callback=callbacks,
                    callback_args=[self.__id]
                )

        while True:
            print("{}: session start".format(self.__id))
            r = self.__sr.start(name="StartRecognition",
                    payload={
                        "format":"pcm",
                        "sample_rate":16000
                        }
                    )
            if not r:
                print("start failed")
                break
            time.sleep(1)
           
            self.__slices = zip(*(iter(self.__data),) * 640)
            for i in self.__slices:
                self.__sr.send_binary(bytes(i))
                time.sleep(0.01)

            self.__sr.send_text(name="StopRecognition") 
            time.sleep(5)

def multiruntest(num=500):
    for i in range(0, num):
        name = "thread" + str(i)
        t = TestSrCommon(name, "tests/test1.pcm")
        t.start()

nls.enableTrace(True)
multiruntest(1)


