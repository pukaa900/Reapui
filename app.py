#!/usr/bin/env python3
"""Fa'aoga Pygame ma ttsmms mo le talosaga TTS."""

import pygame
import pygame.scrap
import uuid
import re
import os
import soundfile as sf
from ttsmms import TTS

# ── Seti Pygame ─────────────────────────────────────────────────────────────
pygame.init()
pygame.scrap.init()
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
pygame.display.set_caption("REA TTS")
FONT = pygame.font.SysFont("sans", 20)
clock = pygame.time.Clock()

# ── Lanu ma foliga ─────────────────────────────────────────────────────────-
FG = (255, 255, 255)
BG_COLOR = (30, 30, 30)

# ── Vasega Pusa Ulufale ─────────────────────────────────────────────────────
class InputBox:
    def __init__(self, x, y, w, h, text=""):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.active = False
        self.cursor_vis = True
        self.cursor_timer = 0

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.active = self.rect.collidepoint(event.pos)
        if event.type == pygame.KEYDOWN and self.active:
            if event.mod & pygame.KMOD_CTRL:
                if event.key == pygame.K_c:
                    pygame.scrap.put(pygame.SCRAP_TEXT, self.text.encode())
                elif event.key == pygame.K_v:
                    clip = pygame.scrap.get(pygame.SCRAP_TEXT)
                    if clip:
                        self.text += clip.decode()
            elif event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif event.key == pygame.K_RETURN:
                pass
            else:
                self.text += event.unicode

    def update(self):
        self.cursor_timer += 1
        if self.cursor_timer >= 30:
            self.cursor_timer = 0
            self.cursor_vis = not self.cursor_vis

    def draw(self, surf):
        box_surf = pygame.Surface((self.rect.w, self.rect.h), pygame.SRCALPHA)
        box_surf.fill((40, 40, 40, 150))
        pygame.draw.rect(box_surf, FG, box_surf.get_rect(), 2, border_radius=10)
        surf.blit(box_surf, self.rect.topleft)
        txt = FONT.render(self.text, True, FG)
        surf.blit(txt, (self.rect.x + 5, self.rect.y + 5))
        if self.active and self.cursor_vis:
            x = self.rect.x + 5 + txt.get_width() + 1
            pygame.draw.line(surf, FG, (x, self.rect.y + 5), (x, self.rect.y + self.rect.h - 5), 2)

    def get(self):
        return self.text.strip()

# ── Vasega Pusa Tusitusiga ──────────────────────────────────────────────────
class TextBox:
    def __init__(self, x, y, w, h, text=""):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.active = False
        self.cursor = len(text)
        self.cursor_vis = True
        self.cursor_timer = 0
        self.scroll = 0

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.active = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEWHEEL and self.active:
            self.scroll -= event.y
            self.scroll = max(0, min(self.scroll, self.max_scroll()))
        elif event.type == pygame.KEYDOWN and self.active:
            if event.mod & pygame.KMOD_CTRL:
                if event.key == pygame.K_c:
                    pygame.scrap.put(pygame.SCRAP_TEXT, self.text.encode())
                elif event.key == pygame.K_v:
                    clip = pygame.scrap.get(pygame.SCRAP_TEXT)
                    if clip:
                        self.insert(clip.decode())
            elif event.key == pygame.K_BACKSPACE:
                if self.cursor > 0:
                    self.text = self.text[:self.cursor-1] + self.text[self.cursor:]
                    self.cursor -= 1
            elif event.key == pygame.K_RETURN:
                self.insert("\n")
            elif event.key == pygame.K_LEFT:
                self.cursor = max(0, self.cursor - 1)
            elif event.key == pygame.K_RIGHT:
                self.cursor = min(len(self.text), self.cursor + 1)
            elif event.key == pygame.K_UP:
                self.move_cursor_vert(-1)
            elif event.key == pygame.K_DOWN:
                self.move_cursor_vert(1)
            else:
                if event.unicode:
                    self.insert(event.unicode)

    def insert(self, char: str) -> None:
        self.text = self.text[:self.cursor] + char + self.text[self.cursor:]
        self.cursor += len(char)

    def move_cursor_vert(self, direction: int) -> None:
        line_idx, col = self.index_to_linecol(self.cursor)
        lines = self.text.split("\n")
        line_idx = max(0, min(len(lines) - 1, line_idx + direction))
        col = min(len(lines[line_idx]), col)
        self.cursor = self.linecol_to_index(line_idx, col)

    def index_to_linecol(self, idx: int):
        lines = self.text.split("\n")
        cur = 0
        for i, line in enumerate(lines):
            if idx <= cur + len(line):
                return i, idx - cur
            cur += len(line) + 1
        return len(lines) - 1, len(lines[-1])

    def linecol_to_index(self, line: int, col: int) -> int:
        lines = self.text.split("\n")
        idx = 0
        for i in range(line):
            idx += len(lines[i]) + 1
        return idx + col

    def max_scroll(self) -> int:
        lines = self.text.split("\n")
        vis = self.rect.h // FONT.get_linesize()
        return max(0, len(lines) - vis)

    def update(self):
        self.cursor_timer += 1
        if self.cursor_timer >= 30:
            self.cursor_timer = 0
            self.cursor_vis = not self.cursor_vis
        line_idx, _ = self.index_to_linecol(self.cursor)
        vis = self.rect.h // FONT.get_linesize()
        if line_idx < self.scroll:
            self.scroll = line_idx
        elif line_idx >= self.scroll + vis:
            self.scroll = line_idx - vis + 1

    def draw(self, surf):
        box_surf = pygame.Surface((self.rect.w, self.rect.h), pygame.SRCALPHA)
        box_surf.fill((40, 40, 40, 150))
        pygame.draw.rect(box_surf, FG, box_surf.get_rect(), 2, border_radius=10)
        surf.blit(box_surf, self.rect.topleft)
        lines = self.text.split("\n")
        vis = self.rect.h // FONT.get_linesize()
        for i in range(vis):
            idx = self.scroll + i
            if idx >= len(lines):
                break
            txt = FONT.render(lines[idx], True, FG)
            surf.blit(txt, (self.rect.x + 5, self.rect.y + 5 + i * FONT.get_linesize()))
        if self.active and self.cursor_vis:
            line_idx, col = self.index_to_linecol(self.cursor)
            if self.scroll <= line_idx < self.scroll + vis:
                cursor_x = self.rect.x + 5 + FONT.size(lines[line_idx][:col])[0]
                cursor_y = self.rect.y + 5 + (line_idx - self.scroll) * FONT.get_linesize()
                pygame.draw.line(surf, FG, (cursor_x, cursor_y), (cursor_x, cursor_y + FONT.get_linesize()), 2)

# ── Vasega Faamau ───────────────────────────────────────────────────────────
class Button:
    def __init__(self, text: str, x: int, y: int, callback):
        self.text = text
        self.callback = callback
        self.rect = pygame.Rect(x, y, 120, 40)
        self.txt = FONT.render(text, True, FG)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and self.rect.collidepoint(event.pos):
            self.callback()

    def draw(self, surf):
        pygame.draw.rect(surf, (100, 100, 100, 180), self.rect, border_radius=10)
        pygame.draw.rect(surf, FG, self.rect, 2, border_radius=10)
        surf.blit(self.txt, (self.rect.x + 15, self.rect.y + 10))

# ── Galuega TTS ─────────────────────────────────────────────────────────────
def fai_tautala(kode: str, tusitusiga: str, sefe: bool = False) -> None:
    """Fai le tautala po'o le sefe o le faila."""
    if not tusitusiga or not kode:
        print("Leai ni faamaumauga.")
        return
    print(f"Fakagao te reqo: {tusitusiga}")
    try:
        tts = TTS(kode)
        out = tts.synthesis(tusitusiga)
        wav = f"{re.sub(r'[^\w\-]+', '_', tusitusiga) or 'clip'}_{uuid.uuid4().hex[:8]}.wav"
        if sefe:
            sf.write(wav, out["x"], out["sampling_rate"])
            print(f"Ua sefe i le {wav}")
        else:
            wav = "_temp.wav"
            sf.write(wav, out["x"], out["sampling_rate"])
        if os.name == "nt":
            os.system(f"powershell -c (New-Object Media.SoundPlayer '{wav}').PlaySync()")
        else:
            os.system(f"aplay '{wav}'")
    except Exception as e:
        print(f"Sese: {e}")

# ── Fausiaina o Mea UI ─────────────────────────────────────────────────────
lang_box = InputBox(50, 40, 200, 32, text="tha")
text_box = TextBox(50, 100, 700, 300, text="Pisa tusitusiga iinei")
speak_btn = Button("Fa'alogo", 200, HEIGHT - 60, lambda: fai_tautala(lang_box.get(), text_box.text, False))
save_btn = Button("Sefe", 360, HEIGHT - 60, lambda: fai_tautala(lang_box.get(), text_box.text, True))

input_boxes = [lang_box, text_box]
buttons = [speak_btn, save_btn]

# ── Ta'amilosaga Autu ──────────────────────────────────────────────────────
running = True
while running:
    screen.fill(BG_COLOR)
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.VIDEORESIZE:
            WIDTH, HEIGHT = event.w, event.h
            screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
            speak_btn.rect.topleft = (200, HEIGHT - 60)
            save_btn.rect.topleft = (360, HEIGHT - 60)
        for box in input_boxes:
            box.handle_event(event)
        for b in buttons:
            b.handle_event(event)

    for box in input_boxes:
        box.update()
        box.draw(screen)
    for b in buttons:
        b.draw(screen)

    label1 = FONT.render("Tulafono o le gagana:", True, FG)
    screen.blit(label1, (50, 15))
    label2 = FONT.render("Tusitusiga e tautala:", True, FG)
    screen.blit(label2, (50, 75))

    pygame.display.flip()
    clock.tick(30)

pygame.quit()
