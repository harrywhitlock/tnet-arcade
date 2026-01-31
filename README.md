# tnet-arcade

Tiny Python sandbox projects for Tnet.

## Hello World

```bash
python3 hello_world.py
```

## Snake (terminal)

This is a simple Snake game using Python's built-in `curses` (no extra deps).

Controls:
- Arrow keys: move
- p: pause/resume
- r: restart (after game over)
- w: toggle wrap-around walls
- h: help overlay
- s: speed mode (normal/fast)
- q: quit

Run:
```bash
python3 snake.py
# or
python3 snake.py --wrap
python3 snake.py --speed fast
```

Notes:
- Works best in a real terminal (VS Code terminal is usually fine).
