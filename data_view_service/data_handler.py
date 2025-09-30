from ast import Dict
import json
import threading
from typing import List

class SourceDataTick():
    '''
    {"600549.SH": {"timetag": "20250929 10:13:41.153","lastPrice": 28.400000000000002,"open": 28.830000000000002,"high": 28.96,"low": 28.19,"lastClose": 28.32,"amount": 356115392,"volume": 124736,"pvolume": 12473600,"stockStatus": 1,"openInt": 13,"settlementPrice": 0,"lastSettlementPrice": 0,"askPrice": [28.41, 28.42, 28.43, 28.44, 28.45],"bidPrice": [28.400000000000002, 28.39, 28.38, 28.37, 28.36],"askVol": [36, 40, 18, 22, 43],"bidVol": [26, 12, 25, 33, 12]}}
    '''
    def __init__(self):
        # 股票代码
        self.code = None
        # 时间
        self.timetag = None
        # 最新价
        self.lastPrice = None
        # 开盘价
        self.open = None
        # 最高价
        self.high = None
        # 最低价
        self.low = None
        # 收盘价
        self.lastClose = None
        # ？？？？
        self.amount = None
        # 成交量
        self.volume = None
        # 盘后成交量
        self.pvolume = None
        # 股票状态
        self.stockStatus = None
        self.openInt = None
        # 结算价
        self.settlementPrice = None
        self.lastSettlementPrice = None
        #买家报价
        self.askPrice = List[float]
        # 卖家报价
        self.bidPrice = List[float]
        # 买家量
        self.askVol = List[int]
        # 卖家量
        self.bidVol = List[int]
        


class SourceData():
    def __init__(self):
        self.类型 = None
        self.timetag = None
        self.data = List[SourceDataTick]
        self.计算仓位 = None
        self.仓位结果 = None
        self.当前仓位 = None
        self.成分股涨数 = None
        self.总成分股数 = None
        self.order_volume = None
        self.target_value = None
        self.最新价 = None
        self.买入ETF = None
        self.名称 = None
        self.买入数量 = None
        self.目标仓位 = None

class FinalDataLine():

    def __init__(self):
        # 更新时间
        self.updateTime = None
        # 指数代码
        self.etfCode = None
        # 指数名称
        self.etfName = None
        # M5信号
        self.m5Signal = None
        # 总分数
        self.totalScore = None
        # 持有状态
        self.holdStatus = None
        # M5占比
        self.m5Percent = None
        # M10占比
        self.m10Percent = None
        # M20信号
        self.m20Percent = None
        # Ma均值占比
        self.maMeanRatio = None
        # M0信号
        self.m0Percent = None
        # 大于M5价格
        self.greaterThanM5Price = None
        # 大于M10价格
        self.greaterThanM10Price = None
        # 大于M20价格
        self.greaterThanM20Price = None
        # 大于M0价格
        self.greaterThanM0Price = None
        # 增长股数量
        self.growthStockCount = None
        # 总股数
        self.totalStockCount = None
    
    def to_dict(self):
        """将对象转换为字典，用于JSON序列化"""
        return {
            'updateTime': self.updateTime,
            'etfCode': self.etfCode,
            'etfName': self.etfName,
            'm5Signal': self.m5Signal,
            'totalScore': self.totalScore,
            'holdStatus': self.holdStatus,
            'm5Percent': self.m5Percent,
            'm10Percent': self.m10Percent,
            'm20Percent': self.m20Percent,
            'maMeanRatio': self.maMeanRatio,
            'm0Percent': self.m0Percent,
            'greaterThanM5Price': self.greaterThanM5Price,
            'greaterThanM10Price': self.greaterThanM10Price,
            'greaterThanM20Price': self.greaterThanM20Price,
            'greaterThanM0Price': self.greaterThanM0Price,
            'growthStockCount': self.growthStockCount,
            'totalStockCount': self.totalStockCount,
        }


class DataHandler:
    
    def __init__(self, notify_sse_clients):
        self.data_record: list[FinalDataLine] = []
        self.notify_sse_clients = notify_sse_clients
        # 每隔5秒推送一次数据
        # self.timer = threading.Timer(5, self.notify_sse_clients)
        # self.timer.start()
        
    def get_all_data(self) -> list[FinalDataLine]:
        return self.data_record
    
    def get_all_data_dict(self) -> list[dict]:
        """返回所有数据的字典列表，用于JSON序列化"""
        return [data.to_dict() for data in self.data_record]
    
    # 获取指定代码的记录，没有则返回空列表
    def get_data_by_code(self, code: str) -> FinalDataLine:
        return next((data for data in self.data_record if data.etfCode == code), None)

    def accept(self, data: SourceData) -> None:
        # 数据处理，SSE 通知更新
        final_data = self.get_data_by_code(data['买入ETF'])
        if final_data is None:
            final_data = FinalDataLine()
            final_data.etfCode = data['买入ETF']
            final_data.etfName = data['名称']
            self.data_record.append(final_data)
        
        final_data.updateTime = data['timetag']
        final_data.growthStockCount = data['成分股涨数']
        final_data.totalStockCount = data['总成分股数']
        
        if data['类型'] == "加仓M5股票":
            self.update_record(final_data, data, "m5Percent","greaterThanM5Price")
        elif data['类型'] == "加仓M10股票":
            self.update_record(final_data, data, "m10Percent","greaterThanM10Price")
        elif data['类型'] == "加仓M20股票":
            self.update_record(final_data, data, "m20Percent","greaterThanM20Price")
        elif data['类型'] == "加仓M0股票":
            self.update_record(final_data, data, "m0Percent","greaterThanM0Price")
        
        # M5信号，如果 m5Percent 大于 0.5，则 m5Signal 为 "加仓"，否则为 "减仓"
        if final_data.m5Percent is not None:
            if final_data.m5Percent > 0.5:
                final_data.m5Signal = "多"
            else:
                final_data.m5Signal = "空"
        
        # TODO ???????
        final_data.holdStatus = data['仓位结果'] == 1
        final_data.maMeanRatio = None
        final_data.totalScore = None

    def update_record(self, final_data: FinalDataLine,sourceData: SourceData, key1: str, key2: str) -> None:
        current_price = sourceData['最新价']
        # 均价（更具 data 计算）
        full_tick = None
        
        full_tick = self.convert_json_to_ticks(sourceData['data'])
        average_price = self.get_average_price(full_tick)
        
        setattr(final_data, key1, average_price['greater_than_average_percent'])
        setattr(final_data, key2, current_price > average_price['average_price'])
        
    # 返回均价和大于均值的占比
    def get_average_price(self, tickList: List[SourceDataTick]):
        average_price = sum(tick.lastPrice for tick in tickList) / len(tickList)
        greater_than_average_percent = sum(1 for tick in tickList if tick.lastPrice > average_price) / len(tickList)
        return {
            'greater_than_average_percent': greater_than_average_percent,
            'average_price': average_price,
        }
    

    def convert_json_to_ticks(self, json_string: str) -> List[SourceDataTick]:
        data_dict = json.loads(json_string)
        ticks_list = []
        for code, data in data_dict.items():
            tick = SourceDataTick()
            tick.code = code
            tick.timetag = data.get("timetag")
            tick.lastPrice = data.get("lastPrice")
            tick.open = data.get("open")
            tick.high = data.get("high")
            tick.low = data.get("low")
            tick.lastClose = data.get("lastClose")
            tick.amount = data.get("amount")
            tick.volume = data.get("volume")
            tick.pvolume = data.get("pvolume")
            tick.stockStatus = data.get("stockStatus")
            tick.openInt = data.get("openInt")
            tick.settlementPrice = data.get("settlementPrice")
            tick.lastSettlementPrice = data.get("lastSettlementPrice")
            tick.askPrice = data.get("askPrice", [])
            tick.bidPrice = data.get("bidPrice", [])
            tick.askVol = data.get("askVol", [])
            tick.bidVol = data.get("bidVol", [])
            ticks_list.append(tick)
        return ticks_list