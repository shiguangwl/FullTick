from __future__ import annotations

import logging
import threading
from dataclasses import asdict, dataclass
from typing import Any

from data_stock_name import get_stock_name

# 配置日志
logger = logging.getLogger(__name__)

# 常量定义
SCORE_THRESHOLD = 0.5  # 评分阈值


@dataclass
class FinalDataLine:
    """股票数据记录."""

    # 更新时间
    update_time: str | None = None
    # 指数代码
    etf_code: str | None = None
    # 指数名称
    etf_name: str | None = None
    # M5信号
    m5_signal: str | None = None
    # 总分数
    total_score: int | None = None
    # M5占比
    m5_percent: float | None = None
    # M10占比
    m10_percent: float | None = None
    # M20占比
    m20_percent: float | None = None
    # Ma均值
    ma_mean_ratio: float | None = None
    # M0占比
    m0_percent: float | None = None
    # 大于M5价格
    greater_than_m5_price: bool | None = None
    # 大于M10价格
    greater_than_m10_price: bool | None = None
    # 大于M20价格
    greater_than_m20_price: bool | None = None
    # 增长股数量
    growth_stock_count: int | None = None
    # 总股数
    total_stock_count: int | None = None
    # 最新价格
    latest_price: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """将对象转换为字典."""
        # 转换为驼峰命名以保持API兼容性
        result = asdict(self)
        return {
            "updateTime": result["update_time"],
            "etfCode": result["etf_code"],
            "etfName": result["etf_name"],
            "m5Signal": result["m5_signal"],
            "totalScore": result["total_score"],
            "m5Percent": result["m5_percent"],
            "m10Percent": result["m10_percent"],
            "m20Percent": result["m20_percent"],
            "maMeanRatio": result["ma_mean_ratio"],
            "m0Percent": result["m0_percent"],
            "greaterThanM5Price": result["greater_than_m5_price"],
            "greaterThanM10Price": result["greater_than_m10_price"],
            "greaterThanM20Price": result["greater_than_m20_price"],
            "growthStockCount": result["growth_stock_count"],
            "totalStockCount": result["total_stock_count"],
            "latestPrice": result["latest_price"],
        }


class DataHandler:
    """数据处理和计算服务, 专注于数据逻辑处理."""

    def __init__(self) -> None:
        self.data_record: list[FinalDataLine] = []
        self.lock = threading.Lock()

    def get_all_data(self) -> list[dict[str, Any]]:
        """获取所有数据,返回字典列表."""
        return [data.to_dict() for data in self.data_record]

    def get_all_data_dict(self) -> list[dict[str, Any]]:
        """获取所有数据的字典形式."""
        return [data.to_dict() for data in self.data_record]

    def get_data_by_code(self, code: str) -> FinalDataLine | None:
        """获取指定代码的记录, 没有则返回None."""
        return next((data for data in self.data_record if data.etf_code == code), None)

    def get_data_since(self, since_time: str) -> list[dict[str, Any]]:
        """获取指定时间之后的数据."""
        try:
            # 筛选出更新时间大于since_time的数据
            filtered_data = [data for data in self.data_record if data.update_time and data.update_time > since_time]
            return [data.to_dict() for data in filtered_data]
        except Exception:
            logger.exception("按时间筛选数据失败")
            # 如果筛选失败, 返回所有数据
            return self.get_all_data()

    def load_from_dict_list(self, data_list: list[dict[str, Any]]) -> None:
        """从字典列表加载数据(用于持久化服务调用)."""
        with self.lock:
            self.data_record.clear()
            for data_dict in data_list:
                try:
                    # 使用 dataclass 的字段来创建对象
                    update_time = data_dict.get("updateTime")
                    final_data = FinalDataLine(
                        # 时间格式化为 2025-10-11 15:15:36,005  -> 2025-10-11 15:15:36
                        update_time=update_time[:19] if update_time else None,
                        etf_code=data_dict.get("etfCode"),
                        etf_name=data_dict.get("etfName"),
                        m5_signal=data_dict.get("m5Signal"),
                        total_score=data_dict.get("totalScore"),
                        m5_percent=data_dict.get("m5Percent"),
                        m10_percent=data_dict.get("m10Percent"),
                        m20_percent=data_dict.get("m20Percent"),
                        ma_mean_ratio=data_dict.get("maMeanRatio"),
                        m0_percent=data_dict.get("m0Percent"),
                        greater_than_m5_price=data_dict.get("greaterThanM5Price"),
                        greater_than_m10_price=data_dict.get("greaterThanM10Price"),
                        greater_than_m20_price=data_dict.get("greaterThanM20Price"),
                        growth_stock_count=data_dict.get("growthStockCount"),
                        total_stock_count=data_dict.get("totalStockCount"),
                        latest_price=data_dict.get("latestPrice"),
                    )
                    self.data_record.append(final_data)
                except (ValueError, KeyError, TypeError) as e:
                    logger.warning("跳过无效数据记录: %s", e)
                    continue
            logger.info("成功加载 %d 条数据记录", len(self.data_record))

    def accept(self, data_list: list[dict[str, Any]]) -> None:
        """接收并处理数据列表."""
        if not data_list:
            logger.warning("接收到空数据列表")
            return

        processed_count = 0
        error_count = 0

        for data in data_list:
            try:
                logger.debug("开始处理数据项: %s", data)

                # 基础数据验证
                if not isinstance(data, dict):
                    logger.error("数据格式错误, 期望字典类型: %s", type(data))
                    error_count += 1
                    continue

                if "log_type" not in data:
                    logger.error("缺少log_type字段: %s", data)
                    error_count += 1
                    continue

                # 根据类型处理数据
                log_type = data["log_type"]
                match log_type:
                    case "加仓三线":
                        self._handle_three_line(data)
                        processed_count += 1
                    case "加仓M5股票" | "加仓M10股票" | "加仓M20股票" | "加仓M0股票":
                        self._handle_mn_stock(data)
                        processed_count += 1
                    case _:
                        logger.error("未知类型数据: %s", log_type)
                        error_count += 1

            except ValueError:
                logger.exception("数据验证失败")
                error_count += 1
            except KeyError:
                logger.exception("缺少必需字段")
                error_count += 1
            except Exception:
                logger.exception("处理数据异常")
                error_count += 1

        logger.info("数据处理完成: 成功 %d 条, 失败 %d 条", processed_count, error_count)

    def _validate_data(self, data: dict[str, Any], required_fields: list[str]) -> None:
        """验证数据完整性."""
        missing_fields = [field for field in required_fields if field not in data or data[field] is None]
        if missing_fields:
            msg = f"缺少必需字段: {missing_fields}"
            raise ValueError(msg)

    def _get_stock_name_safely(self, etf_code: str) -> str:
        """安全获取股票名称."""
        try:
            stock_info = get_stock_name(etf_code)
            return stock_info["name"] if stock_info else etf_code
        except (ValueError, KeyError, TypeError, ConnectionError) as e:
            logger.warning("获取股票名称失败 %s: %s", etf_code, e)
            return etf_code

    def _get_or_create_final_data(self, etf_code: str) -> FinalDataLine:
        """获取或创建数据记录."""
        final_data = self.get_data_by_code(etf_code)
        if final_data is None:
            final_data = FinalDataLine(etf_code=etf_code, etf_name=self._get_stock_name_safely(etf_code))
            self.data_record.append(final_data)
        return final_data

    def _handle_three_line(self, data: dict[str, Any]) -> None:
        """处理加仓三线数据.

        新的数据结构:
        {
            "timestamp": "2025-10-11 11:14:26,619",
            "log_type": "加仓三线",
            "buy_etf": "159920.SZ",
            "last_price": 1.622,
            "m5": 1.64,
            "m10": 1.635,
            "m20": 1.624
        }.
        """
        # 验证必需字段
        required_fields = ["buy_etf", "timestamp", "last_price", "m5", "m10", "m20"]
        self._validate_data(data, required_fields)

        # 获取或创建数据记录
        final_data = self._get_or_create_final_data(data["buy_etf"])

        # 更新数据(时间格式化为前19个字符)
        timestamp = data["timestamp"]
        final_data.update_time = timestamp[:19] if timestamp else None
        final_data.latest_price = data["last_price"]

        # 计算价格比较(添加安全检查)
        if final_data.latest_price is not None:
            final_data.greater_than_m5_price = final_data.latest_price > data["m5"]
            final_data.greater_than_m10_price = final_data.latest_price > data["m10"]
            final_data.greater_than_m20_price = final_data.latest_price > data["m20"]

        self.cal_score()

    def _handle_mn_stock(self, data: dict[str, Any]) -> None:
        """处理加仓Mn股票数据.

        新的数据结构:
        {
            "timestamp": "2025-10-11 11:48:32,020",
            "log_type": "加仓M5股票",
            "buy_etf": "512690.SH",
            "rise_count": 13,
            "total_count": 31,
            "last_price": 0.583,
        }.
        """
        # 验证必需字段
        required_fields = [
            "buy_etf",
            "timestamp",
            "rise_count",
            "total_count",
            "last_price",
        ]
        self._validate_data(data, required_fields)

        # 获取或创建数据记录
        final_data = self._get_or_create_final_data(data["buy_etf"])

        # 更新基础数据(时间格式化为前19个字符)
        timestamp = data["timestamp"]
        final_data.update_time = timestamp[:19] if timestamp else None
        data_type = data["log_type"]

        # 安全计算仓位: 涨的数量 / 总的数量
        total_count = data["total_count"]
        if total_count == 0:
            logger.warning("总数量为0, 无法计算仓位: %s", data)
            calculated_position = 0.0
        else:
            calculated_position = round(data["rise_count"] / total_count, 2)

        # 使用字典映射简化条件判断
        type_mapping: dict[str, Any] = {
            "加仓M5股票": lambda: self._handle_m5_stock(final_data, calculated_position, data),
            "加仓M10股票": lambda: setattr(final_data, "m10_percent", calculated_position),
            "加仓M20股票": lambda: setattr(final_data, "m20_percent", calculated_position),
            "加仓M0股票": lambda: setattr(final_data, "m0_percent", calculated_position),
        }

        if data_type in type_mapping:
            type_mapping[data_type]()
        else:
            logger.warning("未知的股票类型: %s", data_type)

        self.cal_ma_mean()
        self.cal_score()

    def _handle_m5_stock(
        self,
        final_data: FinalDataLine,
        calculated_position: float,
        data: dict[str, Any],
    ) -> None:
        """处理M5股票的特殊逻辑."""
        final_data.m5_percent = calculated_position
        final_data.m5_signal = "多" if final_data.m5_percent > SCORE_THRESHOLD else "空"
        final_data.growth_stock_count = data["rise_count"]
        final_data.total_stock_count = data["total_count"]

    def cal_ma_mean(self) -> None:
        """计算MA均值."""
        for data in self.data_record:
            # 只有当三个百分比都存在时才计算均值
            if data.m5_percent is not None and data.m10_percent is not None and data.m20_percent is not None:
                ma_mean = (data.m5_percent + data.m10_percent + data.m20_percent) / 3
                data.ma_mean_ratio = round(ma_mean, 2)
            else:
                data.ma_mean_ratio = None

    def cal_score(self) -> None:
        """计算分数."""
        # 判断[m5,m10,m20,m0]Percent是否大于阈值 大于则算一分
        # 如果 greater_than_m5_price,greater_than_m10_price,greater_than_m20_price 都为True 则算一分
        for data in self.data_record:
            total_score = 0
            if data.m5_percent is not None and data.m5_percent > SCORE_THRESHOLD:
                total_score += 1
            if data.m10_percent is not None and data.m10_percent > SCORE_THRESHOLD:
                total_score += 1
            if data.m20_percent is not None and data.m20_percent > SCORE_THRESHOLD:
                total_score += 1
            if data.m0_percent is not None and data.m0_percent > SCORE_THRESHOLD:
                total_score += 1
            if data.ma_mean_ratio is not None and data.ma_mean_ratio > SCORE_THRESHOLD:
                total_score += 1
            if data.greater_than_m5_price is True:
                total_score += 1
            if data.greater_than_m10_price is True:
                total_score += 1
            if data.greater_than_m20_price is True:
                total_score += 1

            data.total_score = total_score
