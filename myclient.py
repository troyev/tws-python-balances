import ibapi
import os
import time
import logging
import datetime
import re
from ibapi import wrapper
from ibapi.client import EClient
from ibapi.contract import Contract
from ibapi.utils import iswrapper
from ibapi.account_summary_tags import AccountSummaryTags
from ibapi.common import MarketDataTypeEnum
from decimal import Decimal
from ibapi.ticktype import * # @UnusedWildImport

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger()

class GoogleSheet():
    def __init__(self):
        self.SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
        self.SPREADSHEET_ID = "1jVFrwZLnpjC68GEZZwHo0kNO3cx3ARajTLutFPrp0VQ"
        self.creds = None
        # The file token.json stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if os.path.exists("token.json"):
            self.creds = Credentials.from_authorized_user_file("token.json", self.SCOPES)
        # If there are no (valid) credentials available, let the user log in.
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    "credentials.json", self.SCOPES
                )
                self.creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open("token.json", "w") as token:
                token.write(self.creds.to_json())
        try:
            service = build("sheets", "v4", credentials=self.creds)
            self.sheet = service.spreadsheets()
        except HttpError as err:
            print(err)

    def cell_to_grid_range(self, cell):
        match = re.match(r"([A-Z]+)(\d+)", cell)
        col = match.group(1)
        row = int(match.group(2)) - 1
        col_num = 0
        for char in col:
            col_num = col_num * 26 + (ord(char) - ord('A') + 1)
        col_num -= 1
        return row, col_num

    def writeCell(self, cell, value, decimals=False):
        start_row_index, start_column_index = self.cell_to_grid_range(cell)
        if decimals:
            currency_format = {
                "type": "NUMBER",
                "pattern": "0.00"
            }
        else:
            currency_format = {
                "type": "CURRENCY",
                "pattern": "$#,##0"
            }
        try:
            requests = [
                {
                    "updateCells": {
                        "range": {
                            "sheetId": 0,
                            "startRowIndex": start_row_index,
                            "endRowIndex": start_row_index + 1,
                            "startColumnIndex": start_column_index,
                            "endColumnIndex": start_column_index + 1
                        },
                        "rows": [
                            {
                                "values": [
                                    {
                                        "userEnteredValue": {
                                            "numberValue": value
                                        },
                                        "userEnteredFormat": {
                                            "numberFormat": currency_format
                                        }
                                    }
                                ]
                            }
                        ],
                        "fields": "userEnteredValue,userEnteredFormat.numberFormat"
                    }
                }
            ]

            # Execute the batchUpdate request
            response = self.sheet.batchUpdate(
                spreadsheetId=self.SPREADSHEET_ID,
                body={"requests": requests}
            ).execute()
        except HttpError as err:
            print(err)

                        
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
    def __init__(self, sheet):
        wrapper.EWrapper.__init__(self)
        self.sheet : GoogleSheet = sheet
        self.lastUpdate = datetime.datetime.fromtimestamp(0)

    def setClient(self, client):
        self.client = client

    @iswrapper
    # ! [nextvalidid]
    def nextValidId(self, orderId: int):
        super().nextValidId(orderId)
        logger.info("NextValidId:"+ str(orderId))
        self.client.reqAccountSummary(9001, "All", AccountSummaryTags.AllTags)

        self.SPY = Contract()
        self.SPY.symbol = "SPY"
        self.SPY.secType = "STK"
        self.SPY.currency = "USD"
        self.SPY.exchange = "SMART"
        self.client.reqMktData(1001, self.SPY, "", False, False, [])

    @iswrapper
    def tickPrice(self, reqId, tickType: TickType, price: float,
                  attrib):
        super().tickPrice(reqId, tickType, price, attrib)
        now = datetime.datetime.now()
        if tickType == TickTypeEnum.ASK:
            if (now - self.lastUpdate) >= datetime.timedelta(seconds=5):
                self.lastUpdate = now
                self.sheet.writeCell("D1", price, decimals=True)

    @iswrapper
    def accountSummary(self, reqId: int, account: str, tag: str, value: str,
                       currency: str):
        super().accountSummary(reqId, account, tag, value, currency)
        logger.info(f"AccountSummary. ReqId: {reqId} Account: {account}"
              f" Tag: {tag} Value: {value} Currency: {currency}")
        if "NetLiq" in tag:
            if account[-1] == "1":
                self.sheet.writeCell(cell="B5", value=value)
            if account[-1] == "9":
                self.sheet.writeCell(cell="B6", value=value)
            if account[-1] == "7":
                self.sheet.writeCell(cell="B7", value=value)
            if account[-1] == "4":
                self.sheet.writeCell(cell="B8", value=value)
            print(account, tag, value)

    @iswrapper
    def accountSummaryEnd(self, reqId: int):
        super().accountSummaryEnd(reqId)
        logger.info(f"AccountSummaryEnd. ReqId: {reqId}")
        

class TestClient(EClient):
    def __init__(self, wrapper):
        EClient.__init__(self, wrapper)

if __name__ == "__main__":
    g = GoogleSheet()
    g.writeCell(cell="D1", value=0)
    g.writeCell(cell="B5", value=0)
    g.writeCell(cell="B6", value=0)
    g.writeCell(cell="B7", value=0)
    g.writeCell(cell="B8", value=0)
    SetupLogger()
    try:
        wrapper = TestWrapper(sheet=g)
        client = TestClient(wrapper)
        wrapper.setClient(client)
        logger.info('connecting')
        client.connect("127.0.0.1", 7499, clientId=0)
        print("serverVersion:%s connectionTime:%s" % (client.serverVersion(),
                                                      client.twsConnectionTime()))

        client.run()
    except:
        raise