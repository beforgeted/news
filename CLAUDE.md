# AI Daily Digest

## 运行环境

所有 Python 命令必须在 `news` conda 环境中执行：

```bash
conda run -n news python -m pytest tests/ -v
conda run -n news python -m src.main
conda run -n news pip install <package>
```

环境已创建，依赖已安装，不要在主环境或其他环境中运行本项目代码。
