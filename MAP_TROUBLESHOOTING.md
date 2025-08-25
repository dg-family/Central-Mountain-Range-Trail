# 🗺️ 地圖故障排除指南

## 問題：找不到 GPX 檔案

### 原因分析
瀏覽器由於安全政策（CORS）無法直接訪問本地文件，導致GPX檔案無法載入。

### 解決方案

#### 方法1：使用本地HTTP服務器（推薦）

1. **啟動服務器**：
   ```bash
   cd /path/to/Central-Mountain-Range-Trail
   python3 start-server.py
   ```

2. **訪問網頁**：
   - 地圖測試：http://localhost:8000/simple-map-test.html
   - 行程表：http://localhost:8000/index.html
   - 補給點：http://localhost:8000/supplies.html

#### 方法2：使用其他HTTP服務器

**Python 3**：
```bash
python3 -m http.server 8000
```

**Node.js**：
```bash
npx http-server -p 8000
```

**PHP**：
```bash
php -S localhost:8000
```

### 驗證步驟

1. **檢查控制台**：
   - 打開瀏覽器開發者工具（F12）
   - 查看 Console 標籤
   - 應該看到 "GPX 文件載入成功" 的訊息

2. **測試地圖功能**：
   - 點擊每天的「地圖」按鈕
   - 地圖應該正常顯示
   - 點擊行程項目應該能定位到地圖上的標記

### 常見錯誤

#### 錯誤1：CORS Policy
```
Access to fetch at 'file:///...' from origin 'null' has been blocked by CORS policy
```
**解決**：使用HTTP服務器而不是直接打開HTML文件

#### 錯誤2：404 Not Found
```
Failed to load resource: the server responded with a status of 404
```
**解決**：檢查文件路徑是否正確

#### 錯誤3：GPX解析失敗
```
GPX parsing failed
```
**解決**：檢查GPX文件格式是否正確

### 文件結構
```
Central-Mountain-Range-Trail/
├── index.html              # 主行程表
├── supplies.html           # 補給點頁面
├── simple-map-test.html   # 地圖測試頁面
├── start-server.py        # 本地服務器
├── assets/
│   └── gpx/
│       ├── D1.gpx         # 第一天路線
│       ├── D2.gpx         # 第二天路線
│       ├── D3.gpx         # 第三天路線
│       └── D4.gpx         # 第四天路線
└── styles/
    ├── main.css
    ├── components.css
    └── ...
```

### 技術細節

- **地圖庫**：Leaflet.js + Leaflet-GPX
- **地圖服務**：OpenStreetMap
- **文件格式**：GPX 1.1
- **編碼**：UTF-8

### 支援的瀏覽器

- Chrome 60+
- Firefox 55+
- Safari 12+
- Edge 79+

### 聯繫支援

如果問題仍然存在，請：
1. 檢查瀏覽器控制台的錯誤訊息
2. 確認所有文件都存在且路徑正確
3. 嘗試使用不同的瀏覽器
