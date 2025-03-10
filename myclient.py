import ibapi
import os
import time
import logging
import datetime
from ibapi import wrapper
from ibapi.client import EClient
from ibapi.utils import iswrapper
from ibapi.account_summary_tags import AccountSummaryTags

logger = logging.getLogger()

def SetupLogger():
    if not os.path.exists("log"):
        os.makedirs("log")

    time.strftime("pyibapi.%Y%m%d_%H%M%S.log")

    recfmt = '(%(threadName)s) %(asctime)s.%(msecs)03d %(levelname)s %(filename)s:%(lineno)d %(message)s'

    timefmt = '%y%m%d_%H:%M:%S'

    # logging.basicConfig( level=logging.DEBUG,
    #                    format=recfmt, datefmt=timefmt)
    logging.basicConfig(filename=time.strftime("log/pyibapi.%y%m%d_%H%M%S.log"),
                        filemode="w",
                        level=logging.INFO,
                        format=recfmt, datefmt=timefmt)
    logger = logging.getLogger()
    console = logging.StreamHandler()
    #console.setLevel(logging.INFO)
    #logger.addHandler(console)

class TestWrapper(wrapper.EWrapper):
    def __init__(self):
        wrapper.EWrapper.__init__(self)

    def setClient(self, client):
        self.client = client

    @iswrapper
    # ! [nextvalidid]
    def nextValidId(self, orderId: int):
        super().nextValidId(orderId)
        logger.info("NextValidId:"+ str(orderId))
        self.client.reqAccountSummary(9001, "All", AccountSummaryTags.AllTags)

    @iswrapper
    def accountSummary(self, reqId: int, account: str, tag: str, value: str,
                       currency: str):
        super().accountSummary(reqId, account, tag, value, currency)
        logger.info(f"AccountSummary. ReqId: {reqId} Account: {account}"
              f" Tag: {tag} Value: {value} Currency: {currency}")
        if "NetLiq" in tag:
            print(account, tag, value)

    @iswrapper
    def accountSummaryEnd(self, reqId: int):
        super().accountSummaryEnd(reqId)
        logger.info(f"AccountSummaryEnd. ReqId: {reqId}")
        

class TestClient(EClient):
    def __init__(self, wrapper):
        EClient.__init__(self, wrapper)

if __name__ == "__main__":
    SetupLogger()
    try:
        wrapper = TestWrapper()
        client = TestClient(wrapper)
        wrapper.setClient(client)
        logger.info('connecting')
        client.connect("127.0.0.1", 7499, clientId=0)
        print("serverVersion:%s connectionTime:%s" % (client.serverVersion(),
                                                      client.twsConnectionTime()))

        client.run()
    except:
        raise