# 中央山脈大縱走 - CSS 樣式指南

## 概述

本專案採用模組化的 CSS 架構，將樣式分離到不同的文件中，以提高可維護性和可重用性。

## 文件結構

```
styles/
├── README.md           # 本文件
├── main.css           # 主要樣式表（導入所有模組）
├── variables.css      # CSS 變數和主題定義
├── base.css          # 基礎樣式和重置
├── components.css    # 組件樣式
├── responsive.css    # 響應式設計
└── animations.css    # 動畫效果
```

## 文件說明

### 1. `variables.css`
- **用途**: 定義全局 CSS 變數
- **內容**: 顏色、間距、字體、陰影、過渡等設計令牌
- **特點**: 集中管理主題，易於修改和維護

```css
:root {
  --accent: #3b82f6;
  --spacing-md: 12px;
  --radius-lg: 10px;
}
```

### 2. `base.css`
- **用途**: 基礎樣式和重置
- **內容**: 元素重置、基礎排版、通用樣式
- **特點**: 提供一致的基礎樣式

### 3. `components.css`
- **用途**: 組件樣式
- **內容**: 行程卡片、選單、地圖、標籤等組件
- **特點**: 可重用的組件樣式

### 4. `responsive.css`
- **用途**: 響應式設計
- **內容**: 媒體查詢、斷點、適配樣式
- **特點**: 支援各種設備和螢幕尺寸

### 5. `animations.css`
- **用途**: 動畫效果
- **內容**: 關鍵幀動畫、過渡效果、動畫類別
- **特點**: 豐富的動畫庫和工具類

### 6. `main.css`
- **用途**: 主要樣式表
- **內容**: 導入所有模組、全局覆蓋、補充樣式
- **特點**: 單一入口點，易於管理

## 使用方法

### 在 HTML 中引入
```html
<link rel="stylesheet" href="styles/main.css" />
```

### 使用 CSS 變數
```css
.my-element {
  background: var(--bg-primary);
  color: var(--text-primary);
  padding: var(--spacing-md);
  border-radius: var(--radius-lg);
}
```

### 使用工具類
```html
<div class="flex gap-md items-center">
  <div class="card hover-lift">
    <h3 class="card-title">標題</h3>
  </div>
</div>
```

### 使用動畫類別
```html
<div class="animate-fade-in animate-scale-in">
  動畫內容
</div>
```

## 設計系統

### 顏色系統
- **主要顏色**: `--accent`, `--accent-hover`
- **狀態顏色**: `--ok`, `--warn`, `--bad`, `--info`
- **背景色階**: `--bg-primary`, `--bg-secondary`, `--bg-tertiary`
- **文字色階**: `--text-primary`, `--text-secondary`, `--text-muted`

### 間距系統
- **基礎單位**: 4px
- **間距等級**: `--spacing-xs` (4px) 到 `--spacing-2xl` (32px)

### 字體系統
- **字體大小**: `--text-xs` (12px) 到 `--text-3xl` (32px)
- **字體粗細**: `--font-normal` (400) 到 `--font-bold` (700)

### 圓角系統
- **圓角等級**: `--radius-sm` (6px) 到 `--radius-full` (999px)

## 響應式斷點

- **大螢幕**: 1200px+
- **中等螢幕**: 768px - 1199px
- **平板**: 768px 以下
- **手機**: 480px 以下
- **超小螢幕**: 360px 以下

## 瀏覽器支援

- **現代瀏覽器**: Chrome 90+, Firefox 88+, Safari 14+, Edge 90+
- **CSS Grid**: 支援
- **CSS Custom Properties**: 支援
- **CSS Animations**: 支援
- **Flexbox**: 支援

## 無障礙支援

- **焦點管理**: 清晰的焦點樣式
- **減少動畫**: 支援 `prefers-reduced-motion`
- **高對比度**: 支援 `prefers-contrast: high`
- **螢幕閱讀器**: 適當的語義標記

## 自定義和擴展

### 添加新變數
在 `variables.css` 中添加新的 CSS 變數：

```css
:root {
  --my-custom-color: #ff6b6b;
  --my-custom-spacing: 24px;
}
```

### 添加新組件
在 `components.css` 中添加新的組件樣式：

```css
.my-component {
  background: var(--bg-secondary);
  padding: var(--spacing-md);
  border-radius: var(--radius-md);
}
```

### 添加新動畫
在 `animations.css` 中添加新的動畫：

```css
@keyframes myAnimation {
  from { opacity: 0; }
  to { opacity: 1; }
}

.animate-my-animation {
  animation: myAnimation 0.5s ease-out;
}
```

## 最佳實踐

1. **使用 CSS 變數**: 避免硬編碼值
2. **組件化思維**: 將樣式組織成可重用的組件
3. **響應式優先**: 從移動設備開始設計
4. **性能優化**: 使用適當的動畫和過渡
5. **無障礙設計**: 考慮各種用戶需求

## 故障排除

### 樣式未載入
- 檢查文件路徑是否正確
- 確認 `main.css` 中的 `@import` 語句
- 檢查瀏覽器開發者工具的網路面板

### 變數未生效
- 確認 `variables.css` 已正確導入
- 檢查 CSS 變數語法是否正確
- 確認瀏覽器支援 CSS 變數

### 響應式問題
- 檢查媒體查詢語法
- 確認斷點設置是否正確
- 測試不同設備和螢幕尺寸

## 更新日誌

- **v1.0.0**: 初始模組化 CSS 架構
- 支援響應式設計
- 完整的動畫系統
- 無障礙功能支援
