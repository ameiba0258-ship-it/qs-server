#!/bin/bash
# 企业信息查询工具 - 服务器部署脚本
# 用法: ssh root@你的IP 'bash -s' < deploy.sh

set -e

echo "========================================"
echo "  开始部署到服务器..."
echo "========================================"

# 1. 安装 Docker
if ! command -v docker &> /dev/null; then
    echo "📦 安装 Docker..."
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
fi

# 2. 安装 Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "📦 安装 Docker Compose..."
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
fi

# 3. 拉取代码
echo "📥 拉取代码..."
if [ -d "qs-server" ]; then
    cd qs-server && git pull
else
    git clone https://github.com/ameiba0258-ship-it/qs-server.git
    cd qs-server
fi

# 4. 配置 .env
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "⚠ 请编辑 .env 填入你的 API Key: vim .env"
fi

# 5. 启动
echo "🚀 启动服务..."
docker-compose up -d --build

echo ""
echo "✅ 部署完成!"
echo "   访问: http://服务器IP:9876"
echo "   后台: http://服务器IP:9876/admin"
