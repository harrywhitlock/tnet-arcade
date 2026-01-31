#!/usr/bin/env python3
"""Terminal Snake (curses).

Controls:
- Arrow keys: move
- p: pause/resume
- r: restart (from game over screen)
- q: quit
- w: toggle wrap-around walls

No external dependencies.

Notes:
- Stores a local high score at ~/.config/tnet-arcade/highscore.json
"""

from __future__ import annotations

import argparse
import curses
import json
import os
import random
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path


# --- Defaults / Settings ---
DEFAULT_WRAP_WALLS = False
START_LENGTH = 3
TICK_START = 0.10
TICK_MIN = 0.045
TICK_DECAY_PER_POINT = 0.0025  # speed up as score increases

HIGHSCORE_PATH = Path(os.path.expanduser("~/.config/tnet-arcade/highscore.json"))


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


def wrap_point(p: Point, h: int, w: int) -> Point:
    """Wrap point within the playable area (1..h-2, 1..w-2)."""
    py = 1 + ((p.y - 1) % (h - 2))
    px = 1 + ((p.x - 1) % (w - 2))
    return Point(py, px)


def clamp(n: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, n))


def load_highscore() -> int:
    try:
        data = json.loads(HIGHSCORE_PATH.read_text())
        hs = int(data.get("high_score", 0))
        return max(0, hs)
    except Exception:
        return 0


def save_highscore(score: int) -> None:
    HIGHSCORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = HIGHSCORE_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps({"high_score": int(score)}, indent=2) + "\n")
    tmp.replace(HIGHSCORE_PATH)


def place_food(h: int, w: int, snake: set[Point]) -> Point:
    """Place food on an empty cell.

    Fast path: random tries.
    Dense-board fallback: scan all empty cells.
    """
    playable = (h - 2) * (w - 2)
    empty = playable - len(snake)
    if empty <= 0:
        return Point(1, 1)

    # If board is dense, scanning is more reliable.
    if empty < max(20, playable // 8):
        empties: list[Point] = []
        for y in range(1, h - 1):
            for x in range(1, w - 1):
                p = Point(y, x)
                if p not in snake:
                    empties.append(p)
        return random.choice(empties)

    for _ in range(200):
        p = Point(random.randint(1, h - 2), random.randint(1, w - 2))
        if p not in snake:
            return p

    # Fallback: scan
    for y in range(1, h - 1):
        for x in range(1, w - 1):
            p = Point(y, x)
            if p not in snake:
                return p

    return Point(1, 1)


def draw_border(win: "curses._CursesWindow") -> None:
    win.border()


def calc_tick(score: int) -> float:
    return max(TICK_MIN, TICK_START - (score * TICK_DECAY_PER_POINT))


def centered(win: "curses._CursesWindow", y: int, text: str) -> None:
    h, w = win.getmaxyx()
    x = max(1, (w - len(text)) // 2)
    try:
        win.addstr(y, x, text[: w - 2])
    except curses.error:
        pass


def new_game(h: int, w: int) -> tuple[deque[Point], set[Point], Point, Point, int]:
    start = Point(h // 2, w // 2)
    body = deque([Point(start.y, start.x - i) for i in range(START_LENGTH)])
    snake_set = set(body)
    direction = DIRS[curses.KEY_RIGHT]
    score = 0
    food = place_food(h, w, snake_set)
    return body, snake_set, food, direction, score


def run(stdscr: "curses._CursesWindow", *, wrap_walls: bool) -> int:
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.keypad(True)

    random.seed()

    h, w = stdscr.getmaxyx()
    if h < 12 or w < 24:
        stdscr.addstr(0, 0, "Terminal too small for Snake. Resize and try again.")
        stdscr.refresh()
        time.sleep(2.0)
        return 1

    body, snake_set, food, direction, score = new_game(h, w)
    paused = False
    high_score = load_highscore()

    while True:
        # resize handling
        nh, nw = stdscr.getmaxyx()
        if (nh, nw) != (h, w):
            h, w = nh, nw
            stdscr.clear()
            head = body[0]
            head = Point(clamp(head.y, 1, h - 2), clamp(head.x, 1, w - 2))
            body[0] = head
            snake_set = set(body)
            food = place_food(h, w, snake_set)

        key = stdscr.getch()
        if key in (ord("q"), ord("Q")):
            return 0
        if key in (ord("p"), ord("P")):
            paused = not paused
        if key in (ord("w"), ord("W")):
            wrap_walls = not wrap_walls
        if key in DIRS and not paused:
            nd = DIRS[key]
            if not (nd.y == -direction.y and nd.x == -direction.x):
                direction = nd

        if paused:
            stdscr.erase()
            draw_border(stdscr)
            centered(stdscr, h // 2 - 1, "Paused")
            centered(stdscr, h // 2, "p resume | w toggle wrap | q quit")
            stdscr.refresh()
            time.sleep(0.06)
            continue

        head = body[0]
        new_head = add(head, direction)

        if wrap_walls:
            new_head = wrap_point(new_head, h, w)
        else:
            if (
                new_head.y <= 0
                or new_head.y >= h - 1
                or new_head.x <= 0
                or new_head.x >= w - 1
            ):
                break

        tail = body[-1]
        if new_head in snake_set and new_head != tail:
            break

        body.appendleft(new_head)
        snake_set.add(new_head)

        ate = new_head == food
        if ate:
            score += 1
            if score > high_score:
                high_score = score
            food = place_food(h, w, snake_set)
        else:
            removed = body.pop()
            snake_set.remove(removed)

        # render
        stdscr.erase()
        draw_border(stdscr)
        wrap_txt = "wrap:on" if wrap_walls else "wrap:off"
        hud = f" Snake | score: {score} | best: {high_score} | {wrap_txt} | p pause | q quit "
        centered(stdscr, 0, hud)

        # food
        try:
            stdscr.addch(food.y, food.x, "*")
        except curses.error:
            pass

        for i, p in enumerate(body):
            ch = "@" if i == 0 else "o"
            try:
                stdscr.addch(p.y, p.x, ch)
            except curses.error:
                pass

        stdscr.refresh()
        time.sleep(calc_tick(score))

    # game over
    save_highscore(high_score)

    stdscr.nodelay(False)
    while True:
        stdscr.erase()
        draw_border(stdscr)
        centered(stdscr, h // 2 - 2, "Game Over")
        centered(stdscr, h // 2 - 1, f"Score: {score}")
        centered(stdscr, h // 2, f"Best: {high_score}")
        centered(stdscr, h // 2 + 1, "r restart | w toggle wrap | q quit")
        stdscr.refresh()
        k = stdscr.getch()
        if k in (ord("q"), ord("Q")):
            return 0
        if k in (ord("w"), ord("W")):
            wrap_walls = not wrap_walls
        if k in (ord("r"), ord("R")):
            stdscr.nodelay(True)
            body, snake_set, food, direction, score = new_game(h, w)
            paused = False
            break


def main() -> int:
    parser = argparse.ArgumentParser(prog="snake")
    parser.add_argument(
        "--wrap",
        action="store_true",
        default=DEFAULT_WRAP_WALLS,
        help="Wrap around walls (instead of dying on collision)",
    )
    args = parser.parse_args()

    return curses.wrapper(lambda s: run(s, wrap_walls=args.wrap))


if __name__ == "__main__":
    raise SystemExit(main())
