#!/bin/bash

# Vector 日志等级配置
# 可选值: trace, debug, info, warn, error
# trace - 最详细的日志,包含所有调试信息
# debug - 调试级别,显示详细的处理信息
# info  - 信息级别,显示一般运行信息(默认)
# warn  - 警告级别,仅显示警告和错误
# error - 错误级别,仅显示错误信息
export VECTOR_LOG=info

cd client && ./vector/bin/vector --config ./config/vector.yml