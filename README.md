# DI 统计工具

云服务问题单 DI 统计工具。

## 安装

```bash
pip install -r requirements.txt
```

## 使用

```bash
streamlit run app.py
```

## 功能

- 支持多 Domain 配置爬取（默认 Domain 11 和 33921）
- 爬取问题单数据（自动处理分页）
- DI 统计计算
- 按微服务分组展示
- 按发现问题版本过滤
- Excel 导出

## 配置说明

### 认证信息
- Cookie：从浏览器开发者工具复制
- Authorization Token：JWT Token
- x-titan-userid：用户 ID

### Domain 配置
- 支持多个 Domain，用逗号分隔
- 默认：11, 33921
- 支持的格式：如 `11` 或 `11, 33921`
