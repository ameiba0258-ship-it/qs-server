# 📍 企业信息查询工具

> 多渠道聚合查询平台 · 支持高德/百度/腾讯地图 · 会员管理系统

---

## ✨ 功能特性

### 🔍 多数据源搜索
| 数据源 | 免费额度 | 适合场景 |
|--------|----------|----------|
| 高德地图 | 5,000次/天 | 本地生活、餐饮、购物 |
| 百度地图 | ~4,000次/天 | 企业电话互补覆盖 |
| 腾讯地图 | 1,000,000次/月 | 批量查询、数据分析 |

### 📊 核心功能
- **智能手机号识别** — 自动区分手机号和座机号
- **区县精准定位** — 按区县筛选同城商家
- **多关键词合并** — 同时搜索多个品类，合并去重
- **深度搜索** — 直辖市按区县、省份按城市自动拆分搜索
- **一键导出** — Excel/CSV/JSON 三种格式

### 👥 会员系统
| 等级 | 日搜索上限 | 导出 | 深度搜索 | 多关键词 |
|------|-----------|------|----------|---------|
| 免费 | 50次 | 3次/天 | ❌ | ❌ |
| 会员 ¥99/月 | 5,000次 | 不限 | ✅ | ✅ |
| 企业 | 50,000次 | 不限 | ✅ | ✅ |

### 💳 支付集成
- 支持微信 / 支付宝收款码
- 用户付款后管理员一键确认开通
- 完整的会员等级管理后台

### 🔌 API 接口
- RESTful API，支持 JSON
- API Key 认证（`Authorization: Bearer <key>`）
- 完整的 API 文档（`/api-docs`）
- 在线测试工具

---

## 🚀 快速开始

### 方式一：Docker 部署（推荐）

```bash
# 1. 克隆项目
git clone <your-repo-url>
cd 客资线索

# 2. 配置 API Key
vim .env  # 填入你的高德/百度/腾讯 API Key

# 3. 启动服务
docker-compose up -d

# 4. 访问
open http://localhost:9876
```

### 方式二：直接运行

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置 API Key
cp .env.example .env
# 编辑 .env 填入你的 API Key

# 3. 启动服务
bash start.sh
# 或
python3 -m uvicorn main:app --host 0.0.0.0 --port 9876 --loop asyncio --http h11
```

### 方式三：本地开发

```bash
python3 -m uvicorn main:app --host 127.0.0.1 --port 9876 --loop asyncio --http h11 --reload
```

---

## 📖 使用指南

### 1. 获取 API Key

| 平台 | 注册地址 | 步骤 |
|------|---------|------|
| 高德地图 | https://lbs.amap.com | 控制台 → 应用管理 → 创建应用 → Key（Web服务） |
| 百度地图 | https://lbsyun.baidu.com | 控制台 → 应用管理 → 创建应用（服务端类型） |
| 腾讯地图 | https://lbs.qq.com | 控制台 → 应用管理 → 创建应用 |

### 2. 管理员账号

- **默认用户名**: `admin`
- **默认密码**: `admin123456`
- **访问地址**: `http://localhost:9876/admin`

首次使用请登录管理后台，配置 API Key 和支付信息。

### 3. 用户注册

访问 `http://localhost:9876/login` 注册账号。
注册后即可使用免费版功能。

---

## 🏗 项目结构

```
├── main.py                 # FastAPI 服务入口
├── config.py               # 配置管理
├── auth_db.py              # 用户/会员/API Token 数据库
├── stats_tracker.py        # 使用统计追踪
├── export_utils.py         # Excel/CSV/JSON 导出
│
├── providers/              # 数据源适配层
│   ├── base.py             # 抽象基类
│   ├── amap.py             # 高德地图
│   ├── baidumap.py         # 百度地图
│   └── tencentmap.py       # 腾讯地图
│
├── static/                 # 前端静态文件
│   ├── index.html          # 搜索首页
│   ├── css/style.css       # 样式
│   ├── js/app.js           # 前端逻辑
│   ├── auth/login.html     # 登录页
│   ├── membership.html     # 会员升级页
│   ├── admin.html          # 管理后台
│   └── api/docs.html       # API 文档
│
├── data/                   # 数据文件
│   ├── regions.json        # 全国省市区数据
│   ├── poi_types.json      # POI 类型分类
│   ├── payment_config.json # 支付配置
│   ├── stats.json          # 使用统计
│   └── users.db            # SQLite 用户库
│
├── Dockerfile              # Docker 构建
├── docker-compose.yml      # Docker 编排
├── requirements.txt        # Python 依赖
└── start.sh                # 启动脚本
```

---

## 🛠 管理后台

访问 `/admin`，登录后可进行：

### 用户管理
- 查看所有注册用户
- 设置会员等级（免费/会员/企业/管理员）
- 查看每日使用量

### 支付设置
- 设置微信号
- 设置支付宝账号
- 上传收款二维码图片 URL
- 设置会员价格

### 付款通知
- 查看用户付款申请
- 一键确认并开通会员

### API Token 管理
- 生成/撤销 API Token
- 设置 Token 等级（免费/会员/企业）

---

## 🔌 API 接口

### 认证方式
```bash
# Header 方式（推荐）
Authorization: Bearer YOUR_API_KEY

# URL 参数方式
?api_key=YOUR_API_KEY
```

### 搜索接口
```http
POST /api/search
Content-Type: application/json
Authorization: Bearer YOUR_API_KEY

{
    "keyword": "律师事务所",
    "province": "北京市",
    "provider": "amap",
    "page_size": 20
}
```

### 批量搜索
```http
POST /api/batch-search
Content-Type: application/json
Authorization: Bearer YOUR_API_KEY

{
    "keyword": "律师事务所",
    "province": "广东省",
    "keywords": ["法律咨询", "律师"]  // 多关键词
}
```

完整文档请访问 `/api-docs`。

---

## 🐳 Docker 部署

### 服务器要求
- CPU: 1核+
- 内存: 1GB+
- 硬盘: 10GB+
- Docker: 20.10+

### 部署步骤

```bash
# 1. 服务器上安装 Docker
curl -fsSL https://get.docker.com | sh

# 2. 克隆项目
git clone <your-repo-url>
cd 客资线索

# 3. 配置 API Key
vim .env

# 4. 启动
docker-compose up -d

# 5. 配置 Nginx 反代（可选）
# 参考 nginx.conf 配置 HTTPS 和域名
```

### 数据持久化
- `./data/` — 数据库、配置、统计文件
- `./exports/` — 导出的 Excel 文件
- `./.env` — API Key 配置

---

## 📝 常见问题

**Q: 搜索返回"每日查询超限"？**
A: 高德/百度免费额度已用完，可在配置中添加其他数据源，或升级开发者套餐。

**Q: 如何重置管理员密码？**
A: 删除 `data/users.db` 后重启服务，会自动重建并创建默认管理员。

**Q: 如何增加搜索数量？**
A: 使用深度搜索（选择省份不选城市），系统会自动按城市拆分搜索后合并去重。

---

## 📄 许可证

本项目仅供合法商业查询使用。请遵守各数据源平台的使用条款。

---

*Built with ❤️ by Codex*
