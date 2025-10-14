from __future__ import annotations

import logging
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

from config import config

# 配置日志
logger = logging.getLogger(__name__)

# 常量定义
HTTP_OK = 200  # HTTP 成功状态码


def query_sina_api(stock_code: str) -> str | None:
    """使用新浪财经API查询.

    Args:
        stock_code: 完整股票代码, 如 "513050.SH" 或 "513050.SZ"
    """
    try:
        # 解析股票代码和市场后缀
        if "." in stock_code:
            code, market = stock_code.split(".")
            prefix = market.lower()  # SH -> sh, SZ -> sz
        else:
            logger.debug("股票代码格式错误, 缺少市场后缀: %s", stock_code)
            return None

        url = f"http://hq.sinajs.cn/list={prefix}{code}"
        response = requests.get(url, timeout=config.stock_api_timeout)
        response.raise_for_status()

        content = response.text
        if "var hq_str_" in content:
            data = content.split('"')[1].split(",")
            if len(data) > 0 and data[0]:
                return str(data[0])  # 股票名称在第一个位置
    except (ValueError, ConnectionError, TimeoutError) as e:
        logger.debug("新浪API查询失败: %s", e)
    return None


def query_eastmoney_api(stock_code: str) -> str | None:
    """使用东方财富API查询.

    Args:
        stock_code: 完整股票代码, 如 "513050.SH" 或 "513050.SZ"
    """
    try:
        # 解析股票代码和市场后缀
        if "." in stock_code:
            code, market = stock_code.split(".")
            # 东方财富API: 1=上海, 0=深圳
            market_id = "1" if market.upper() == "SH" else "0"
        else:
            logger.debug("股票代码格式错误, 缺少市场后缀: %s", stock_code)
            return None

        url = f"http://push2.eastmoney.com/api/qt/stock/get?secid={market_id}.{code}&fields=f57,f58,f107,f162"
        response = requests.get(url, timeout=config.stock_api_timeout)
        if response.status_code == HTTP_OK:
            data = response.json()
            if data.get("data") and data["data"].get("f58"):
                return str(data["data"]["f58"])
    except (ValueError, ConnectionError, TimeoutError) as e:
        logger.debug("东方财富API查询失败: %s", e)
    return None


def query_tencent_api(stock_code: str) -> str | None:
    """使用腾讯财经API查询.

    Args:
        stock_code: 完整股票代码, 如 "513050.SH" 或 "513050.SZ"
    """
    try:
        # 解析股票代码和市场后缀
        if "." in stock_code:
            code, market = stock_code.split(".")
            prefix = market.lower()  # SH -> sh, SZ -> sz
        else:
            logger.debug("股票代码格式错误, 缺少市场后缀: %s", stock_code)
            return None

        url = f"http://qt.gtimg.cn/q={prefix}{code}"
        response = requests.get(url, timeout=config.stock_api_timeout)
        if response.status_code == HTTP_OK:
            content = response.text
            if "~" in content:
                data = content.split("~")
                if len(data) > 1 and data[1]:
                    return str(data[1])  # 股票名称
    except (ValueError, ConnectionError, TimeoutError) as e:
        logger.debug("腾讯API查询失败: %s", e)
    return None


def normalize_stock_code(stock_code: str) -> str | None:
    """
    标准化股票代码为统一格式 XXXXXX.SH 或 XXXXXX.SZ.

    支持的输入格式:
    - 513050.SH (带上海后缀) -> 513050.SH
    - 513050.SZ (带深圳后缀) -> 513050.SZ
    - SH513050 (上海前缀) -> 513050.SH
    - SZ513050 (深圳前缀) -> 513050.SZ

    Args:
        stock_code (str): 原始股票代码

    Returns:
        str: 标准化为 XXXXXX.SH 或 XXXXXX.SZ 格式, 如果无法标准化则返回None
    """
    if not stock_code:
        return None

    # 转换为大写并去除空白
    code = stock_code.strip().upper()

    # 情况1: 已经是标准格式 (如 513050.SH, 513050.SZ)
    if re.match(r"^\d{6}\.(SH|SZ)$", code):
        return code

    # 情况2: 带前缀格式 (如 SH513050, SZ513050) -> 转换为 513050.SH / 513050.SZ
    if re.match(r"^(SH|SZ)\d{6}$", code):
        market = code[:2]
        number = code[2:]
        return f"{number}.{market}"

    # 无法识别的格式
    return None


def validate_stock_code(stock_code: str) -> bool:
    normalized = normalize_stock_code(stock_code)
    return normalized is not None


def get_stock_name(stock_code: str) -> dict[str, str] | None:
    """
    使用多个数据源并行查询股票名称.

    Args:
        stock_code (str): 股票代码, 支持格式: "513050.SH", "513050.SZ", "SH513050", "SZ513050"

    Returns:
        dict: 包含code、name、source的字典, 如果未找到则返回 None
            例如: {"code": "513050.SH", "name": "中概互联网ETF", "source": "腾讯财经API"}
    """
    # 标准化股票代码为 XXXXXX.SH 或 XXXXXX.SZ 格式
    normalized_code = normalize_stock_code(stock_code)
    if not normalized_code:
        logger.warning("无法标准化股票代码: %s", stock_code)
        return None

    logger.debug("标准化后的股票代码: %s", normalized_code)

    # 定义所有查询方法和对应的渠道名称
    query_methods = [
        ("新浪财经API", query_sina_api),
        ("东方财富API", query_eastmoney_api),
        ("腾讯财经API", query_tencent_api),
    ]

    # 使用线程池并行查询
    with ThreadPoolExecutor(max_workers=config.stock_api_max_workers) as executor:
        # 提交所有查询任务, 使用标准化的完整代码(包含.SH/.SZ后缀)
        future_to_source = {
            executor.submit(method, normalized_code): source_name for source_name, method in query_methods
        }

        # 获取第一个成功的结果
        for future in as_completed(future_to_source):
            source_name = future_to_source[future]
            try:
                result = future.result()
                if result:
                    # 取消其他未完成的任务
                    for f in future_to_source:
                        if f != future:
                            f.cancel()

                    return {
                        "code": normalized_code,
                        "name": result.strip(),  # 去除可能的空白字符
                        "source": source_name,
                    }
            except (ValueError, ConnectionError, TimeoutError) as e:
                logger.debug("%s查询失败: %s", source_name, e)
                continue

    logger.warning("所有API都未能查询到股票信息: %s", normalized_code)
    return None


def main() -> None:
    """主函数: 处理命令行参数或用户输入."""
    if len(sys.argv) > 1:
        # 从命令行参数获取股票代码
        stock_code = sys.argv[1].strip()
    else:
        # 从用户输入获取股票代码
        stock_code = input(
            "请输入股票代码(如 513050.SH, 513050.SZ, SH513050, SZ513050): ",
        ).strip()

    if not stock_code:
        logger.error("错误: 股票代码不能为空")
        return

    # 验证股票代码格式
    if not validate_stock_code(stock_code):
        logger.error("错误: 股票代码格式不正确")
        logger.info("支持的格式:")
        logger.info("  - 带后缀: 513050.SH, 513050.SZ")
        logger.info("  - 带前缀: SH513050, SZ513050")
        return

    logger.info("正在查询股票代码: %s", stock_code)

    result = get_stock_name(stock_code)

    if result:
        logger.info("股票代码: %s", result["code"])
        logger.info("股票名称: %s", result["name"])
        logger.info("查询渠道: %s", result["source"])
    else:
        logger.warning("未找到股票代码 %s 对应的股票信息", stock_code)


if __name__ == "__main__":
    main()
