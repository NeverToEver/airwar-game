# 项目规则

## 虚拟环境

**项目使用 Python 虚拟环境 (`venv`)**，路径：`d:\Trae\pygames_dev\venv`

### Python 可执行文件
- **必须使用**：`d:\Trae\pygames_dev\venv\Scripts\python.exe`
- **不要使用**系统级的 `python` 或 `python3`

### 运行命令示例

```powershell
# 运行游戏
d:\Trae\pygames_dev\venv\Scripts\python.exe main.py

# 运行测试
d:\Trae\pygames_dev\venv\Scripts\python.exe -m pytest airwar/tests/ -v

# 安装依赖
d:\Trae\pygames_dev\venv\Scripts\pip install pygame
```

### 虚拟环境信息
- Python 版本：3.11.9
- 位置：`d:\Trae\pygames_dev\venv`
- 类型：Python venv（隔离环境）

## 代码规范

- 代码文件使用英文注释
- 配置文件和文档可使用中文
- 遵循 PEP 8 代码风格
