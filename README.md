# Facebook Ads 周报系统

## 📁 文件结构

```
trea_al/
├── weekly-report.html          # 前端周报页面（主入口）
├── fb_ads_data.json            # 同步的广告数据
├── 启动后端服务.ps1            # PowerShell 启动脚本（推荐）
├── 启动后端服务.bat            # CMD 启动脚本（备用）
├── README.md                   # 使用说明
└── backend/
    ├── server.py               # 后端服务（Facebook API）
    └── test_api.py             # API 测试脚本
```

## 🚀 快速开始

### 1. 启动后端服务

**方式一：PowerShell（推荐）**
```powershell
# 在 PowerShell 中执行
.\启动后端服务.ps1
```

或右键点击 `启动后端服务.ps1` → 选择「使用 PowerShell 运行」

**方式二：CMD（备用）**
```cmd
双击运行：启动后端服务.bat
```

**方式三：手动执行**
```bash
cd backend
python server.py
```

### 2. 打开周报页面

双击 `weekly-report.html` 用浏览器打开

### 3. 同步 Facebook 数据

1. 点击页面顶部的「同步FB数据」按钮
2. 在弹窗中选择日期范围：
   - 开始日期 / 结束日期
   - 或使用快速选择（最近7天/30天/90天、本月、上月）
3. 点击「开始同步」
4. 同步完成后，页面会显示数据时间范围和详细统计

## 🔌 API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/sync` | POST | 同步广告数据 |
| `/api/data` | GET | 获取已保存数据 |
| `/api/accounts` | GET | 获取账户列表 |
| `/api/token-status` | GET | 检查 Token 状态 |

## ⚙️ 配置信息

已配置的 Facebook 广告账户：
- 英国站 (SUNLU UK) - ID: 1450908062157108
- 法国站 (SUNLU FR) - ID: 1263004614711858
- 德国站 (SUNLU.DE.WEZO) - ID: 567253999563537
- 意大利站 (SUNLU IT) - ID: 2194106121024447

## 📝 注意事项

- 后端服务运行在 `http://localhost:5000`
- Token 已设置为永久有效
- 数据自动保存到 `fb_ads_data.json`
- 首次运行可能需要安装依赖（脚本会自动检查并安装）

## 🔧 故障排除

**PowerShell 执行策略问题**
如果提示「无法加载脚本，因为在此系统上禁止运行脚本」，请执行：
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```
然后选择 `Y` 确认。
