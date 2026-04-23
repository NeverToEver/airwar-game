# Air War - 飞机大战

一款使用 Python + Pygame 开发的 2D 太空射击游戏。

## 快速开始

```bash
pip install -r requirements.txt
python main.py
```

## 游戏操作

| 按键 | 功能 |
|------|------|
| 方向键 / WASD | 移动 |
| 空格键 | 射击 |
| ESC | 暂停 |
| H (长按) | 停靠母舰存档 |
| K (长按3秒) | 投降 |

## 游戏特色

- 三种难度模式，动态难度调整
- 18 种 Buff 系统
- 母舰存档机制
- 多种敌人类型（直线、正弦、锯齿、俯冲、悬停、螺旋）
- Boss 战

## 技术栈

- Python 3.x + Pygame + Pillow
- 架构：Scene Pattern, Manager Pattern, Observer Pattern