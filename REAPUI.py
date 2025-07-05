#!/usr/bin/env python3
import pygame, uuid, re, os, soundfile as sf
from ttsmms import TTS

pygame.init()

WIDTH, HEIGHT = 600, 360
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("REA TTS GUI")

# ── now that a window exists, init clipboard ───────────────────────────
pygame.scrap.init()
pygame.scrap.set_mode(pygame.SCRAP_CLIPBOARD)

FONT  = pygame.font.SysFont("sans", 20)
clock = pygame.time.Clock()

CURSOR_BLINK_MS = 500
SCROLLBAR_W, MIN_SLIDER_H = 12, 20

# ── GUI widgets ──────────────────────────────────────────────────────────
class ScrollableInputBox:
    def __init__(self, x, y, w, h, text=''):
        self.rect = pygame.Rect(x, y, w, h)
        self.inner_w, self.inner_h = w - SCROLLBAR_W - 6, h - 6
        self.text, self.cursor_pos = text, len(text)
        self.active, self.scroll = False, 0
        self.dragging_bar, self.drag_offset_px = False, 0
        self.last_blink, self.cursor_visible = pygame.time.get_ticks(), True
        self.sel_start = self.sel_end = None
        self.lines, self.line_starts = [], []
        self.slider_rect = pygame.Rect(0, 0, 0, 0)

    # ---------- helpers --------------------------------------------------
    def has_sel(self):      return self.sel_start is not None and self.sel_start != self.sel_end
    def clear_sel(self):    self.sel_start = self.sel_end = None

    def wrap_text(self):
        self.lines, self.line_starts = [], []
        idx = 0
        for para in self.text.split('\n'):
            cur = ''
            for word in para.split(' '):
                nxt = (cur + ' ' + word) if cur else word
                if FONT.size(nxt)[0] <= self.inner_w:
                    cur = nxt
                else:
                    self.lines.append(cur)
                    self.line_starts.append(idx)
                    idx += len(cur) + 1
                    cur = word
            self.lines.append(cur)
            self.line_starts.append(idx)
            idx += len(cur) + 1
        if self.line_starts:
            self.line_starts[-1] = len(self.text) - len(self.lines[-1])

    def visible_lines(self): return self.inner_h // FONT.get_height()
    def clamp_scroll(self):
        self.scroll = max(0, min(self.scroll,
                        max(0, len(self.lines) - self.visible_lines())))

    def update_cursor_blink(self):
        if pygame.time.get_ticks() - self.last_blink >= CURSOR_BLINK_MS:
            self.cursor_visible = not self.cursor_visible
            self.last_blink = pygame.time.get_ticks()

    # ---------- event handling ------------------------------------------
    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.slider_rect.collidepoint(event.pos):
                self.dragging_bar = True
                self.drag_offset_px = event.pos[1] - self.slider_rect.y
            else:
                self.active = self.rect.collidepoint(event.pos)
                if self.active:
                    self.clear_sel()
                    cx, cy = event.pos[0] - self.rect.x - 3, event.pos[1] - self.rect.y - 3
                    line_i = self.scroll + cy // FONT.get_height()
                    if 0 <= line_i < len(self.lines):
                        col = 0
                        for col in range(len(self.lines[line_i]) + 1):
                            if FONT.size(self.lines[line_i][:col])[0] >= cx:
                                break
                        self.cursor_pos = self.line_starts[line_i] + col
                        self.cursor_visible = True
                        self.last_blink = pygame.time.get_ticks()

        elif event.type == pygame.MOUSEBUTTONUP:
            self.dragging_bar = False

        elif event.type == pygame.MOUSEMOTION and self.dragging_bar:
            track = self.rect.h
            bar_h = self.slider_rect.h
            max_start = max(0, len(self.lines) - self.visible_lines())
            if max_start:
                new_y = max(self.rect.y,
                            min(event.pos[1] - self.drag_offset_px,
                                self.rect.y + track - bar_h))
                self.slider_rect.y = new_y
                self.scroll = int((new_y - self.rect.y) /
                                  (track - bar_h) * max_start)

        elif event.type == pygame.MOUSEWHEEL and self.active:
            self.scroll -= event.y
            self.clamp_scroll()

        elif event.type == pygame.KEYDOWN and self.active:
            ctrl = pygame.key.get_mods() & pygame.KMOD_CTRL
            # ----- clipboard combos -------------------------------------
            if ctrl and event.key == pygame.K_a:           # select-all
                self.sel_start, self.sel_end = 0, len(self.text)
                self.cursor_pos = self.sel_end
            elif ctrl and event.key == pygame.K_c:         # copy
                data = (self.text[self.sel_start:self.sel_end]
                        if self.has_sel() else self.text)
                pygame.scrap.put(pygame.SCRAP_TEXT, data.encode())
            elif ctrl and event.key == pygame.K_x:         # cut
                if self.has_sel():
                    pygame.scrap.put(pygame.SCRAP_TEXT,
                                     self.text[self.sel_start:self.sel_end].encode())
                    start, end = sorted((self.sel_start, self.sel_end))
                    self.text = self.text[:start] + self.text[end:]
                    self.cursor_pos = start
                    self.clear_sel()
            elif ctrl and event.key == pygame.K_v:         # paste
                clip = pygame.scrap.get(pygame.SCRAP_TEXT)
                if clip:
                    clip = clip.decode('utf-8', 'ignore')
                    if self.has_sel():
                        start, end = sorted((self.sel_start, self.sel_end))
                        self.text = self.text[:start] + clip + self.text[end:]
                        self.cursor_pos = start + len(clip)
                        self.clear_sel()
                    else:
                        self.text = (self.text[:self.cursor_pos] + clip +
                                     self.text[self.cursor_pos:])
                        self.cursor_pos += len(clip)

            # ----- editing / nav ---------------------------------------
            else:
                if self.has_sel() and event.key not in (
                        pygame.K_LEFT, pygame.K_RIGHT,
                        pygame.K_UP, pygame.K_DOWN,
                        pygame.K_LSHIFT, pygame.K_RSHIFT):
                    start, end = sorted((self.sel_start, self.sel_end))
                    self.text = self.text[:start] + self.text[end:]
                    self.cursor_pos = start
                    self.clear_sel()

                if event.key == pygame.K_BACKSPACE and self.cursor_pos > 0:
                    self.text = (self.text[:self.cursor_pos - 1] +
                                 self.text[self.cursor_pos:])
                    self.cursor_pos -= 1
                elif event.key == pygame.K_DELETE and self.cursor_pos < len(self.text):
                    self.text = self.text[:self.cursor_pos] + self.text[self.cursor_pos + 1:]
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    self.text = (self.text[:self.cursor_pos] + '\n' +
                                 self.text[self.cursor_pos:])
                    self.cursor_pos += 1
                elif event.key == pygame.K_LEFT and self.cursor_pos > 0:
                    self.cursor_pos -= 1; self.clear_sel()
                elif event.key == pygame.K_RIGHT and self.cursor_pos < len(self.text):
                    self.cursor_pos += 1; self.clear_sel()
                elif event.key == pygame.K_UP:
                    self.move_vert(-1); self.clear_sel()
                elif event.key == pygame.K_DOWN:
                    self.move_vert(+1); self.clear_sel()
                elif event.unicode and not ctrl:
                    self.text = (self.text[:self.cursor_pos] + event.unicode +
                                 self.text[self.cursor_pos:])
                    self.cursor_pos += len(event.unicode)

            self.cursor_visible = True
            self.last_blink = pygame.time.get_ticks()

    def move_vert(self, direction):
        line_i = 0
        for i, start in enumerate(self.line_starts):
            if start <= self.cursor_pos < start + len(self.lines[i]):
                line_i = i
                break
        col = self.cursor_pos - self.line_starts[line_i]
        new = line_i + direction
        if 0 <= new < len(self.lines):
            self.cursor_pos = self.line_starts[new] + min(col, len(self.lines[new]))
            if new < self.scroll:
                self.scroll = new
            elif new >= self.scroll + self.visible_lines():
                self.scroll = new - self.visible_lines() + 1

    # ---------- frame update & draw -------------------------------------
    def update(self):
        self.wrap_text(); self.clamp_scroll(); self.update_cursor_blink()
        vis, total = self.visible_lines(), max(len(self.lines), 1)
        bar_h = max(int(self.rect.h * vis / total), MIN_SLIDER_H)
        max_start = max(0, total - vis)
        self.slider_rect = pygame.Rect(
            self.rect.right - SCROLLBAR_W,
            self.rect.y if max_start == 0
            else self.rect.y + int(self.scroll / max_start * (self.rect.h - bar_h)),
            SCROLLBAR_W, bar_h)

    def draw(self, surf):
        pygame.draw.rect(surf, (230,230,230), self.rect, border_radius=3)
        pygame.draw.rect(surf, (30,144,255) if self.active else (180,180,180),
                         self.rect, 2, border_radius=3)

        line_h = FONT.get_height()
        base_x, base_y = self.rect.x + 3, self.rect.y + 3

        # selection highlight
        if self.has_sel():
            s0, s1 = sorted((self.sel_start, self.sel_end))
            for i in range(self.visible_lines()):
                idx = self.scroll + i
                if idx >= len(self.lines): break
                lstart = self.line_starts[idx]
                lend   = lstart + len(self.lines[idx])
                if lend <= s0 or lstart >= s1: continue
                st_in  = max(s0, lstart) - lstart
                en_in  = min(s1, lend)   - lstart
                x0 = base_x + FONT.size(self.lines[idx][:st_in])[0]
                x1 = base_x + FONT.size(self.lines[idx][:en_in])[0]
                y  = base_y + i * line_h
                pygame.draw.rect(surf, (173,216,230), (x0, y, x1 - x0, line_h))

        # text
        for i in range(self.visible_lines()):
            idx = self.scroll + i
            if idx >= len(self.lines): break
            surf.blit(FONT.render(self.lines[idx], True, (0,0,0)),
                      (base_x, base_y + i * line_h))

        # caret
        if self.active and self.cursor_visible:
            cur_line = 0
            for i, s in enumerate(self.line_starts):
                if s <= self.cursor_pos < s + len(self.lines[i]):
                    cur_line = i; break
            if self.scroll <= cur_line < self.scroll + self.visible_lines():
                col = self.cursor_pos - self.line_starts[cur_line]
                cx  = base_x + FONT.size(self.lines[cur_line][:col])[0]
                cy  = base_y + (cur_line - self.scroll) * line_h
                pygame.draw.line(surf, (0,0,0), (cx, cy), (cx, cy + line_h))

        # scrollbar
        if len(self.lines) > self.visible_lines():
            pygame.draw.rect(surf, (200,200,200),
                (self.rect.right - SCROLLBAR_W, self.rect.y,
                 SCROLLBAR_W, self.rect.h))
            pygame.draw.rect(surf, (100,100,100), self.slider_rect)

    def get(self): return self.text.strip()

class Button:
    def __init__(self, label, x, y, fn):
        self.rect = pygame.Rect(x, y, 120, 40)
        self.fn   = fn
        self.txt  = FONT.render(label, True, (0,0,0))
    def handle_event(self, e):
        if e.type == pygame.MOUSEBUTTONDOWN and self.rect.collidepoint(e.pos):
            self.fn()
    def draw(self, surf):
        pygame.draw.rect(surf, (200,200,200), self.rect, border_radius=4)
        surf.blit(self.txt, (self.rect.x + 15, self.rect.y + 10))

# ── Speak logic (unchanged) --------------------------------------------
def speak(code, text, save=False):
    if not text or not code: return print("Missing input.")
    try:
        out = TTS(code).synthesis(text)
        name = (re.sub(r'\W+', '_', text) or 'clip') + '_' + uuid.uuid4().hex[:8] + '.wav'
        if not save: name = "_temp.wav"
        sf.write(name, out['x'], out['sampling_rate'])
        os.system(f"powershell -c (New-Object Media.SoundPlayer '{name}').PlaySync()"
                  if os.name == 'nt' else f"aplay '{name}'")
    except Exception as e:
        print("Error:", e)

# ── Build UI -----------------------------------------------------------
lang_box = ScrollableInputBox(200, 25, 200, 34, 'tha')
text_box = ScrollableInputBox(50, 85, 500, 180, 'พิมพ์ข้อความที่นี่')
btn_speak = Button("Speak", 150, 280, lambda: speak(lang_box.get(), text_box.get(), False))
btn_save  = Button("Save",  330, 280, lambda: speak(lang_box.get(), text_box.get(), True))

widgets = [lang_box, text_box]
buttons = [btn_speak, btn_save]

# ── Main loop ----------------------------------------------------------
running = True
while running:
    screen.fill((255,255,255))
    screen.blit(FONT.render("Language Code:", True, (0,0,0)), (50, 30))
    screen.blit(FONT.render("Text to Speak:", True, (0,0,0)), (50, 60))

    for e in pygame.event.get():
        if e.type == pygame.QUIT:
            running = False
        for w in widgets: w.handle_event(e)
        for b in buttons: b.handle_event(e)

    for w in widgets: w.update(); w.draw(screen)
    for b in buttons: b.draw(screen)

    pygame.display.flip()
    clock.tick(30)

pygame.quit()
