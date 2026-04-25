# base-rag

插件化AI工具综合平台

## 技术栈

- FastAPI + 简易前端
- 无Docker，Windows本地直接运行

## 快速启动

```bash
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

访问 http://localhost:8000/

## 项目结构

```
├── app/
│   ├── plugins/     # 插件目录
│   ├── tools/       # 工具模块
│   ├── main.py      # 入口
│   ├── config.py    # 配置
│   └── router.py    # 路由
├── static/          # 前端页面
│   ├── index.html
│   ├── tools.html
│   └── settings.html
└── requirements.txt
```

## 插件类型

- 计算工具
- 文本处理
- 结构化AI
- 八字历法
