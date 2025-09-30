import ast
import json
import re
from typing import Any, cast
from logger import Logger
import requests

class DataHandler():
    # 内容匹配
    def match(self, content: str,source_file: str,start_line_number: int) -> bool:
        """匹配段落内容（以空行分隔的段落），如果匹配成功，则返回True，否则返回False"""
        
        pattern = re.compile(r"""
            python.(?P<类型>.+?)\.py.*?
            timetag\s*=\s*(?P<timetag>\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2})
            .*?
            full_tick\s*=\s*\d+\s*(?P<data>\{.*?\})\s*
            计算仓位\s*=\s*(?P<计算仓位>[\d\.]+)\s+
            仓位结果\s*=\s*(?P<仓位结果>\d+)\s+
            当前仓位\s*=\s*(?P<当前仓位>[\d\.]+)\s+
            成分股涨数\s*=\s*(?P<成分股涨数>\d+)\s+
            总成分股数\s*=\s*(?P<总成分股数>\d+)\s+
            order_volume\s*=\s*(?P<order_volume>\d+)\s+
            target_value\s*=\s*(?P<target_value>[\d\.]+)\s+
            最新价\s*=\s*(?P<最新价>[\d\.]+)\s+
            买入ETF\s*=\s*(?P<买入ETF>[\w\.]+)\s+
            名称\s*=\s*(?P<名称>[\u4e00-\u9fa5A-Z]+)\s+
            买入数量\s*=\s*(?P<买入数量>\d+)\s+
            目标仓位\s*=\s*(?P<目标仓位>\d+)\s*
        """, re.VERBOSE | re.DOTALL)

        match = pattern.search(content)

        parsed_data = {}
        if match:
            parsed_data = match.groupdict()

            for key, value in parsed_data.items():
                if value.isdigit():
                    parsed_data[key] = int(value)
                elif '.' in value:
                    try:
                        parsed_data[key] = float(value)
                    except ValueError:
                        pass
        else:
            return False
                    
        # 将data字段转换为JSON文本
        parsed_data['data'] = self._normalize_dict_data(parsed_data['data'])
        
        self.handle(parsed_data)


        return True


    def _normalize_dict_data(self, astJson) -> str:
        """将Python字典字符串转换为JSON文本"""
        parsed_data_ast: object = ast.literal_eval(astJson)
        if isinstance(parsed_data_ast, dict):
            dict_data = cast(dict[str, object], parsed_data_ast)
            return json.dumps(dict_data)
        else:
            return astJson
    
    
    # 匹配成功后的处理
    def handle(self, data: Any) -> None:
        """处理匹配的段落数据（以空行分隔的段落）

        Args:
            data: 匹配的段落内容（可能是多行的）
            line_number: 段落起始行号
            source_file: 源文件名
        """
        # 统计段落信息
        lines = str(data).strip().split('\n')
        line_count = len(lines)

        # 显示数据预览（如果内容太长则截断）
        data_preview = str(data).strip()
        if len(data_preview) > 200:
            data_preview = f"{data_preview[:100]}...{data_preview[-100:]}"

        Logger.info(f"[处理段落数据] {data_preview}")
        # 上传数据
        self.upload_data(data)

    def upload_data(self,data) -> None:
        try:
          result = requests.post("http://localhost:5000/data", json=data, headers={"Secret-Key": "123456"}, timeout=5)
          if result.status_code != 200:
            Logger.error(f"数据投递失败: {result.status_code} {result.text}")
        except requests.exceptions.RequestException as e:
            Logger.error(f"数据投递异常: {e}")