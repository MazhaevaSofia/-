"""Отрисовка учебного сообщения (почта, SMS, мессенджер) для режима
«Фишинг-детектор». draw_message() возвращает «горячие зоны» (отправитель,
абзацы, ссылка, вложение): по ним сцена понимает, на что навёл курсор
игрок, и куда ставить маркеры улик после ответа.
"""
import pygame

from . import theme

AVATAR_COLORS = [
    (56, 189, 248), (52, 211, 153), (251, 191, 36),
    (167, 139, 250), (244, 114, 182), (248, 113, 113),
]
CHANNEL_LABELS = {"email": "Почта", "sms": "SMS", "messenger": "Мессенджер"}
BODY_FONT_SIZE = 19
PADDING = 26
CHROME_HEIGHT = 36
STATUS_HEIGHT = 34
HINT_TEXT = "Наведите курсор на отправителя или ссылку, чтобы увидеть настоящий адрес"


def wrap_text(text, font, max_width):
    words = text.split(" ")
    lines, current = [], ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if font.size(candidate)[0] <= max_width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _avatar(screen, center, radius, name):
    color = AVATAR_COLORS[sum(ord(c) for c in name) % len(AVATAR_COLORS)]
    pygame.draw.circle(screen, color, center, radius)
    letter = theme.font(int(radius * 1.05), bold=True).render(name[:1].upper(), True, theme.TEXT_ON_ACCENT)
    screen.blit(letter, letter.get_rect(center=center))


def _chrome_bar(screen, rect, label, time_text):
    bar = pygame.Rect(rect.x, rect.y, rect.width, CHROME_HEIGHT)
    pygame.draw.rect(screen, theme.SURFACE_ALT, bar,
                     border_top_left_radius=theme.RADIUS_LG, border_top_right_radius=theme.RADIUS_LG)
    pygame.draw.line(screen, theme.BORDER_SOFT, (bar.x, bar.bottom - 1), (bar.right, bar.bottom - 1))
    pygame.draw.circle(screen, theme.ACCENT, (bar.x + 20, bar.centery), 5)
    label_surf = theme.font(theme.FONT_XS, bold=True).render(label, True, theme.TEXT_SECONDARY)
    screen.blit(label_surf, (bar.x + 34, bar.centery - label_surf.get_height() // 2))
    time_surf = theme.font(theme.FONT_XS).render(time_text, True, theme.TEXT_MUTED)
    screen.blit(time_surf, (bar.right - 20 - time_surf.get_width(), bar.centery - time_surf.get_height() // 2))


def _measure_paragraphs(paragraphs, font, max_width, gap):
    blocks = []
    for text in paragraphs:
        lines = wrap_text(text, font, max_width)
        blocks.append((lines, len(lines) * font.get_linesize()))
    total = sum(h for _, h in blocks) + gap * max(0, len(blocks) - 1)
    return blocks, total


def _draw_paragraphs(screen, blocks, font, x, y, max_width, gap, hotspots, color=theme.TEXT_PRIMARY):
    for i, (lines, height) in enumerate(blocks):
        for j, line in enumerate(lines):
            screen.blit(font.render(line, True, color), (x, y + j * font.get_linesize()))
        hotspots[f"p{i}"] = pygame.Rect(x, y, max_width, height)
        y += height + gap
    return y - gap


def _draw_link(screen, link, x, y, max_width, hovered, font, hotspots, boxed):
    text_surf = font.render(link["text"], True, theme.ACCENT)
    if boxed:
        rect = pygame.Rect(x, y, min(max_width, text_surf.get_width() + 32), 40)
        pygame.draw.rect(screen, theme.ELEVATED if hovered else theme.SURFACE_ALT, rect, border_radius=theme.RADIUS_MD)
        pygame.draw.rect(screen, theme.ACCENT if hovered else theme.BORDER, rect, 1, border_radius=theme.RADIUS_MD)
        text_pos = (rect.x + 16, rect.centery - text_surf.get_height() // 2)
    else:
        rect = pygame.Rect(x, y, min(max_width, text_surf.get_width()), text_surf.get_height() + 2)
        text_pos = (x, y)
    screen.blit(text_surf, text_pos)
    underline_y = text_pos[1] + text_surf.get_height() - 1
    pygame.draw.line(screen, theme.ACCENT, (text_pos[0], underline_y), (text_pos[0] + text_surf.get_width(), underline_y))
    hotspots["link"] = rect
    return rect.bottom


def _draw_attachment(screen, attachment, x, y, hotspots):
    rect = pygame.Rect(x, y, 300, 46)
    pygame.draw.rect(screen, theme.SURFACE_ALT, rect, border_radius=theme.RADIUS_MD)
    pygame.draw.rect(screen, theme.BORDER, rect, 1, border_radius=theme.RADIUS_MD)
    icon = pygame.Rect(rect.x + 12, rect.y + 9, 22, 28)
    pygame.draw.rect(screen, theme.TEXT_SECONDARY, icon, border_radius=3)
    pygame.draw.polygon(screen, theme.SURFACE_ALT, [(icon.right - 8, icon.y), (icon.right, icon.y), (icon.right, icon.y + 8)])
    name = theme.font(theme.FONT_SM, bold=True).render(attachment["name"], True, theme.TEXT_PRIMARY)
    size = theme.font(theme.FONT_XS).render(attachment["size"], True, theme.TEXT_MUTED)
    screen.blit(name, (rect.x + 46, rect.y + 5))
    screen.blit(size, (rect.x + 46, rect.y + 25))
    hotspots["attachment"] = rect
    return rect.bottom


def _draw_status_bar(screen, card, text, color):
    bar = pygame.Rect(card.x + 1, card.bottom - STATUS_HEIGHT, card.width - 2, STATUS_HEIGHT - 1)
    pygame.draw.rect(screen, theme.SURFACE_ALT, bar,
                     border_bottom_left_radius=theme.RADIUS_LG, border_bottom_right_radius=theme.RADIUS_LG)
    pygame.draw.line(screen, theme.BORDER_SOFT, (bar.x, bar.y), (bar.right, bar.y))
    font = theme.font(theme.FONT_XS)
    surf = font.render(text, True, color)
    while surf.get_width() > bar.width - 28 and len(text) > 8:
        text = text[:-2]
        surf = font.render(text.rstrip() + "...", True, color)
    screen.blit(surf, (bar.x + 14, bar.centery - surf.get_height() // 2))


def draw_tooltip(screen, text, mouse_pos, bounds):
    font = theme.font(theme.FONT_SM)
    surf = font.render(text, True, theme.TEXT_PRIMARY)
    box = pygame.Rect(0, 0, surf.get_width() + 24, surf.get_height() + 16)
    box.topleft = (mouse_pos[0] + 14, mouse_pos[1] + 18)
    box.clamp_ip(bounds)
    pygame.draw.rect(screen, theme.ELEVATED, box, border_radius=theme.RADIUS_SM)
    pygame.draw.rect(screen, theme.ACCENT, box, 1, border_radius=theme.RADIUS_SM)
    screen.blit(surf, (box.x + 12, box.y + 8))


def draw_message(screen, rect, message, mouse_pos=None, reveal=False):
    """Рисует сообщение в rect. Возвращает {цель: Rect} для наведения и маркеров улик."""
    theme.draw_panel(screen, rect, radius=theme.RADIUS_LG)
    prev_clip = screen.get_clip()
    screen.set_clip(rect)

    channel = message["channel"]
    hotspots = {}
    body_font = theme.font(BODY_FONT_SIZE)
    inner_x = rect.x + PADDING
    inner_w = rect.width - 2 * PADDING
    _chrome_bar(screen, rect, CHANNEL_LABELS[channel], message["time"])
    y = rect.y + CHROME_HEIGHT + 18

    if channel == "email":
        subject_font = theme.font(theme.FONT_LG, bold=True)
        subject_lines = wrap_text(message["subject"], subject_font, inner_w)
        subject_top = y
        for line in subject_lines:
            screen.blit(subject_font.render(line, True, theme.TEXT_PRIMARY), (inner_x, y))
            y += subject_font.get_linesize()
        hotspots["subject"] = pygame.Rect(inner_x, subject_top, inner_w, y - subject_top)
        y += 12

        row = pygame.Rect(inner_x, y, inner_w, 46)
        _avatar(screen, (row.x + 22, row.centery), 21, message["sender_name"])
        name_surf = theme.font(theme.FONT_MD, bold=True).render(message["sender_name"], True, theme.TEXT_PRIMARY)
        screen.blit(name_surf, (row.x + 56, row.y + 2))
        addr_text = f"<{message['sender_addr']}>" if reveal else "кому: вам"
        addr_color = (theme.DANGER if message["is_phishing"] else theme.SUCCESS) if reveal else theme.TEXT_MUTED
        addr_font = theme.font(theme.FONT_XS)
        addr_surf = addr_font.render(addr_text, True, addr_color)
        while addr_surf.get_width() > row.width - 60 and len(addr_text) > 8:
            addr_text = addr_text[:-2]
            addr_surf = addr_font.render(addr_text + "...>", True, addr_color)
        screen.blit(addr_surf, (row.x + 56, row.y + 26))
        hotspots["sender"] = row
        y = row.bottom + 10
        pygame.draw.line(screen, theme.BORDER_SOFT, (inner_x, y), (inner_x + inner_w, y))
        y += 14

        blocks, _ = _measure_paragraphs(message["body"], body_font, inner_w, 10)
        y = _draw_paragraphs(screen, blocks, body_font, inner_x, y, inner_w, 10, hotspots) + 14
        if message["link"]:
            hovered = bool(mouse_pos) and _link_rect_at(inner_x, y, message["link"], body_font, inner_w).collidepoint(mouse_pos)
            y = _draw_link(screen, message["link"], inner_x, y, inner_w, hovered, body_font, hotspots, boxed=True) + 14
        if message["attachment"]:
            _draw_attachment(screen, message["attachment"], inner_x, y, hotspots)
    else:
        if channel == "sms":
            header = pygame.Rect(inner_x, y, inner_w, 74)
            _avatar(screen, (header.centerx, header.y + 22), 22, message["sender_name"])
            name_surf = theme.font(theme.FONT_MD, bold=True).render(message["sender_name"], True, theme.TEXT_PRIMARY)
            screen.blit(name_surf, (header.centerx - name_surf.get_width() // 2, header.y + 50))
        else:
            header = pygame.Rect(inner_x, y, inner_w, 50)
            _avatar(screen, (header.x + 24, header.centery), 22, message["sender_name"])
            name_surf = theme.font(theme.FONT_MD, bold=True).render(message["sender_name"], True, theme.TEXT_PRIMARY)
            screen.blit(name_surf, (header.x + 60, header.y + 4))
            status = theme.font(theme.FONT_XS).render("в сети", True, theme.SUCCESS)
            screen.blit(status, (header.x + 60, header.y + 28))
        hotspots["sender"] = header
        y = header.bottom + 12
        pygame.draw.line(screen, theme.BORDER_SOFT, (inner_x, y), (inner_x + inner_w, y))
        y += 18

        bubble_pad = 16
        bubble_w = min(inner_w, int(rect.width * 0.82))
        text_w = bubble_w - 2 * bubble_pad
        blocks, text_h = _measure_paragraphs(message["body"], body_font, text_w, 8)
        link_h = 0
        if message["link"]:
            link_h = body_font.get_linesize() + 10
        bubble_h = bubble_pad * 2 + text_h + link_h
        bubble = pygame.Rect(inner_x, y, bubble_w, bubble_h)
        pygame.draw.rect(screen, theme.ELEVATED if channel == "messenger" else theme.SURFACE_ALT,
                         bubble, border_radius=theme.RADIUS_LG)
        pygame.draw.rect(screen, theme.BORDER, bubble, 1, border_radius=theme.RADIUS_LG)
        text_bottom = _draw_paragraphs(screen, blocks, body_font, bubble.x + bubble_pad, bubble.y + bubble_pad,
                                       text_w, 8, hotspots)
        if message["link"]:
            link_y = text_bottom + 10
            hovered = bool(mouse_pos) and _link_rect_at(bubble.x + bubble_pad, link_y, message["link"], body_font, text_w, boxed=False).collidepoint(mouse_pos)
            _draw_link(screen, message["link"], bubble.x + bubble_pad, link_y, text_w, hovered, body_font, hotspots, boxed=False)
        time_surf = theme.font(theme.FONT_XS).render(message["time"], True, theme.TEXT_MUTED)
        screen.blit(time_surf, (bubble.x + 6, bubble.bottom + 6))

    hover_target = None
    if mouse_pos:
        for target in ("link", "sender"):
            if target in hotspots and hotspots[target].collidepoint(mouse_pos):
                hover_target = target
                break

    if message["link"] and (reveal or hover_target == "link"):
        status_color = (theme.DANGER if message["is_phishing"] else theme.SUCCESS) if reveal else theme.ACCENT
        _draw_status_bar(screen, rect, f"Адрес ссылки: {message['link']['url']}", status_color)
    elif reveal and not message["link"]:
        _draw_status_bar(screen, rect, "В этом сообщении нет ссылок", theme.TEXT_MUTED)
    else:
        _draw_status_bar(screen, rect, HINT_TEXT, theme.TEXT_MUTED)

    screen.set_clip(prev_clip)

    if hover_target == "sender" and not reveal and message["sender_addr"]:
        draw_tooltip(screen, f"Адрес отправителя: {message['sender_addr']}", mouse_pos, screen.get_rect())
    elif hover_target == "sender" and not reveal:
        draw_tooltip(screen, "Имя отправителя легко подделать", mouse_pos, screen.get_rect())
    return hotspots, hover_target


def _link_rect_at(x, y, link, font, max_width, boxed=True):
    width = font.size(link["text"])[0]
    if boxed:
        return pygame.Rect(x, y, min(max_width, width + 32), 40)
    return pygame.Rect(x, y, min(max_width, width), font.get_linesize())


def draw_clue_markers(screen, hotspots, clues, is_phishing):
    """Обводит улики и нумерует их (номера совпадают со списком пояснений)."""
    color = theme.DANGER if is_phishing else theme.SUCCESS
    number_font = theme.font(theme.FONT_XS, bold=True)
    for number, clue in enumerate(clues, start=1):
        target = hotspots.get(clue["target"])
        if target is None:
            continue
        box = target.inflate(16, 12)
        pygame.draw.rect(screen, color, box, 2, border_radius=theme.RADIUS_SM)
        center = (box.left, box.top)
        pygame.draw.circle(screen, color, center, 10)
        label = number_font.render(str(number), True, theme.TEXT_ON_ACCENT)
        screen.blit(label, label.get_rect(center=center))
