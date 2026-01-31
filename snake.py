#!/usr/bin/env python3
"""Terminal Snake (curses).

- Arrow keys to move
- q to quit

No external dependencies.
"""

from __future__ import annotations

import curses
import random
import time
from collections import deque
from dataclasses import dataclass


@dataclass(frozen=True)
class Point:
    y: int
    x: int


DIRS = {
    curses.KEY_UP: Point(-1, 0),
    curses.KEY_DOWN: Point(1, 0),
    curses.KEY_LEFT: Point(0, -1),
    curses.KEY_RIGHT: Point(0, 1),
}


def add(a: Point, b: Point) -> Point:
    return Point(a.y + b.y, a.x + b.x)


def clamp(n: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, n))


def place_food(h: int, w: int, snake: set[Point]) -> Point:
    # playable area excludes border
    while True:
        p = Point(random.randint(1, h - 2), random.randint(1, w - 2))
        if p not in snake:
            return p


def draw_border(win: "curses._CursesWindow", h: int, w: int) -> None:
    win.border()
    # corners sometimes look odd in some terminals; border() handles it.


def run(stdscr: "curses._CursesWindow") -> int:
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.keypad(True)

    random.seed()

    h, w = stdscr.getmaxyx()
    # minimum playable size
    if h < 12 or w < 24:
        stdscr.addstr(0, 0, "Terminal too small for Snake. Resize and try again.")
        stdscr.refresh()
        time.sleep(2.0)
        return 1

    # game settings
    tick = 0.09  # seconds per frame

    # snake starts centered
    start = Point(h // 2, w // 2)
    body = deque([start, Point(start.y, start.x - 1), Point(start.y, start.x - 2)])
    snake_set = set(body)

    direction = DIRS[curses.KEY_RIGHT]
    pending_key: int | None = None

    food = place_food(h, w, snake_set)
    score = 0

    while True:
        # handle resize
        nh, nw = stdscr.getmaxyx()
        if (nh, nw) != (h, w):
            h, w = nh, nw
            stdscr.clear()
            # keep head inside new bounds
            head = body[0]
            head = Point(clamp(head.y, 1, h - 2), clamp(head.x, 1, w - 2))
            body[0] = head
            snake_set = set(body)
            food = place_food(h, w, snake_set)

        # input
        key = stdscr.getch()
        if key != -1:
            pending_key = key

        if pending_key in DIRS:
            nd = DIRS[pending_key]
            # prevent reversing into yourself
            if not (nd.y == -direction.y and nd.x == -direction.x):
                direction = nd
        elif pending_key in (ord("q"), ord("Q")):
            return 0
        pending_key = None

        head = body[0]
        new_head = add(head, direction)

        # wall collision (border is 0 and h-1/w-1)
        if new_head.y <= 0 or new_head.y >= h - 1 or new_head.x <= 0 or new_head.x >= w - 1:
            break

        # self collision: allow moving into the current tail position (it will move)
        tail = body[-1]
        if new_head in snake_set and new_head != tail:
            break

        body.appendleft(new_head)
        snake_set.add(new_head)

        ate = new_head == food
        if ate:
            score += 1
            food = place_food(h, w, snake_set)
        else:
            removed = body.pop()
            snake_set.remove(removed)

        # render
        stdscr.erase()
        draw_border(stdscr, h, w)

        # HUD
        hud = f" Snake | score: {score} | q to quit "
        stdscr.addstr(0, max(2, (w - len(hud)) // 2), hud[: w - 4])

        # food
        try:
            stdscr.addch(food.y, food.x, "*")
        except curses.error:
            pass

        # snake
        for i, p in enumerate(body):
            ch = "@" if i == 0 else "o"
            try:
                stdscr.addch(p.y, p.x, ch)
            except curses.error:
                pass

        stdscr.refresh()
        time.sleep(tick)

    # game over screen
    stdscr.nodelay(False)
    msg1 = "Game Over"
    msg2 = f"Score: {score}"
    msg3 = "Press any key to exit"
    stdscr.erase()
    draw_border(stdscr, h, w)
    stdscr.addstr(h // 2 - 1, (w - len(msg1)) // 2, msg1)
    stdscr.addstr(h // 2, (w - len(msg2)) // 2, msg2)
    stdscr.addstr(h // 2 + 1, (w - len(msg3)) // 2, msg3)
    stdscr.refresh()
    stdscr.getch()
    return 0


def main() -> int:
    return curses.wrapper(run)


if __name__ == "__main__":
    raise SystemExit(main())
