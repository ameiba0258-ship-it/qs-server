#!/bin/bash
# 商家信息查询工具 - 启动脚本
# 用法: bash start.sh
# 保持此终端打开，关闭即停止服务

cd "$(dirname "$0")"

echo "===================================="
echo "  商家信息查询工具 v2.0"
echo "===================================="
echo ""
echo "  🌐 访问地址: http://localhost:9876"
echo "  🔐 管理员:   http://localhost:9876/admin"
echo "  🏆 会员升级: http://localhost:9876/membership"
echo ""
echo "  管理员账号: admin / admin123456"
echo "===================================="
echo ""

python3 -m uvicorn main:app --host 0.0.0.0 --port 9876 --loop asyncio --http h11
