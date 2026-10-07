#!/usr/bin/env python3
"""Пересобирает все значки netgram из исходников в этом каталоге.

Исходники (набор владельца, не править руками без нужды):
    67-app-icon.svg          круглый значок, от 128 px и выше;
    67-app-icon-small.svg    упрощенный, для 32-64 px;
    67-app-icon-tiny.svg     без цифр, для 16-24 px;
    67-app-icon-macos.svg    скругленный квадрат по сетке macOS;
    67-intro-logo.svg        то же, что 67-app-icon.svg, 480x480;
    67-tray-*.svg            значки трея (плоский самолетик);
    67.ico                   многоразмерный ICO (16..256);
    png/                     готовые растровые экспорты.

Запуск из корня репозитория:
    python Telegram/Resources/art/netgram/make_icons.py [--browser ПУТЬ]

Что пишет:
    Telegram/Resources/art/icon*.png, icon256.ico, logo_256*.png,
        icon_round512@2x.png, icon_green.png, iconbig_green.png;
    Telegram/Resources/art/ayu/<вариант>/app.svg|app.png + app_icon.ico
        (выбор значка в настройках, вариант default - логотип netgram);
    Telegram/Telegram/AppIcon-<Вариант>.icon (те же варианты для macOS);
    Telegram/Telegram/Images.xcassets (значок macOS для сборки без Xcode);
    Telegram/Resources/icons/tray_monochrome*.svg (монохромный трей),
    Telegram/Resources/icons/mac_tray_icon*.png (трей macOS).

SVG растеризуется headless-браузером на Chromium (Edge, Chrome, Chromium):
в окружении сборки другого растеризатора SVG обычно нет. Нужен Pillow.
"""

import argparse
import base64
import os
import shutil
import struct
import subprocess
import sys
import tempfile
from io import BytesIO
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
ART = HERE.parent
RESOURCES = ART.parent
TELEGRAM = RESOURCES.parent
MAC = TELEGRAM / 'Telegram'

ICO_SIZES = (16, 24, 32, 48, 64, 128, 256)

# Геометрия знака из 67-app-icon*.svg. Самолетик - два контура
# в системе координат 182x153, цифры "67" - в системе 1000x1000.
PLANE = (
    'M0,72 L182,0 L78,90 Z',
    'M182,0 L152,153 L98,118 L72,142 L76,98 Z',
)
SIX = ('M245,600 L245,350 C245,275 305,230 385,230 C445,230 492,258 512,305 '
       'L512,390 L415,390 C409,390 405,385 405,379 L405,362 C405,343 396,330 '
       '384,330 C369,330 358,343 358,362 L358,434 C380,418 398,412 412,412 '
       'C480,412 528,465 528,540 L528,610 C528,685 470,728 386,728 C300,728 '
       '245,680 245,600 Z M358,525 C358,507 368,495 384,495 C400,495 409,507 '
       '409,525 L409,600 C409,618 400,630 384,630 C368,630 358,618 358,600 Z')
SEVEN = ('M512,305 L784,305 Q792,305 792,313 L792,398 Q792,405 790,412 '
         'L680,786 Q678,793 670,793 L562,793 Q553,793 556,785 L667,405 '
         'L604,405 L604,432 Q604,440 596,440 L518,440 Q510,440 510,432 Z')

# Размещение знака: (сторона viewBox, сдвиг и масштаб самолетика,
# сдвиг и масштаб цифр внутри самолетика или None - без цифр).
KINDS = {
    'big': (1024, (204.80, 272.54, 3.1508), (87.2, 60, 0.078)),
    'small': (256, (38.40, 57.45, 0.9284), (84, 57, 0.084)),
    'tiny': (64, (8.32, 13.29, 0.2462), None),
    # Слой для AppIcon-Default.icon: квадрат 824 из 67-app-icon-macos.svg
    # растянут на весь холст 1024, фон рисует сам macOS.
    'mac-layer': (1024, (193.86, 267.56, 3.2163), (87.2, 60, 0.078)),
    'tray': (16, (0.32, 1.8525, 0.080875), None),
    # Трей macOS: форма 67-tray-macos-template.svg в рамке прежнего
    # значка tdesktop (30x25 из 44 при @2x), чтобы высота в строке меню
    # и место под счетчик остались прежними.
    'mac-tray': (44, (6.25, 10.10, 0.16213), None),
}

INK = '#1A1A1A'
PAPER = '#F3F3F1'

# Варианты значка на выбор. Ключ - имя каталога art/ayu/<имя>
# и (с заглавной буквы) имя AppIcon-<Имя>.icon.
VARIANTS = {
    'default': {'bg': INK, 'plane': PAPER, 'digits': INK},
    'alt': {'bg': PAPER, 'plane': INK, 'digits': PAPER},
    'discord': {'bg': '#5865F2', 'plane': '#FFFFFF', 'digits': '#5865F2'},
    'spotify': {'bg': '#121212', 'plane': '#1ED760', 'digits': '#121212'},
    'extera': {'bg': '#E83030', 'plane': '#FFFFFF', 'digits': '#E83030'},
    # Белый, к хвосту уходящий в 60% белого поверх красного фона.
    'extera2': {
        'bg': '#E83030',
        'plane': ('#F6ACAC', '#FFFFFF'),
        'digits': '#E83030',
    },
    'nothing': {'bg': '#FDFDFD', 'plane': '#1C1D1F', 'digits': '#D71A21'},
    'bard': {
        'bg': '#FDFDFD',
        'plane': ('#1BA1E3', '#5489D6', '#9B72CB', '#D96570', '#F49C46'),
        'digits': '#FDFDFD',
    },
    'yaplus': {
        'bg': '#FDFDFD',
        'plane': ('#8341EF', '#EB469F', '#FF5C4D'),
        'digits': '#FDFDFD',
    },
}
WIN95 = {
    'bg': '#008080',
    'wing': '#DEDEDE',
    'body': '#B0BAB8',
    'light': '#FFFFFF',
    'shadow': '#27282A',
}


def mark_svg(kind, palette, background=True):
    """SVG без масок и фильтров: его без потерь читает QSvgRenderer."""
    side, (px, py, ps), digits = KINDS[kind]
    plane = palette['plane']
    defs = ''
    if isinstance(plane, tuple):
        last = len(plane) - 1
        stops = ''.join(
            f'<stop offset="{i / last:.2f}" stop-color="{c}"/>'
            for i, c in enumerate(plane))
        defs = ('<defs><linearGradient id="plane" gradientUnits="userSpaceOnUse"'
                f' x1="0" y1="153" x2="182" y2="0">{stops}</linearGradient></defs>')
        plane = 'url(#plane)'
    half = side / 2
    bg = (f'<circle cx="{half:g}" cy="{half:g}" r="{half:g}" fill="{palette["bg"]}"/>'
          if background else '')
    paths = ''.join(f'<path d="{d}"/>' for d in PLANE)
    body = (f'<g fill="{plane}" stroke="{plane}" stroke-width="1.2" '
            f'stroke-linejoin="round">{paths}</g>')
    if digits:
        dx, dy, ds = digits
        body += (f'<g transform="translate({dx:g} {dy:g}) scale({ds:g})" '
                 f'fill="{palette["digits"]}">'
                 f'<path fill-rule="evenodd" d="{SIX}"/><path d="{SEVEN}"/></g>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{side}" '
            f'height="{side}" viewBox="0 0 {side} {side}">{defs}{bg}'
            f'<g transform="translate({px:g} {py:g}) scale({ps:g})">{body}</g>'
            '</svg>\n')


def tray_svg(dot=None):
    """Монохромный трей: белый самолетик, как в 67-tray-dark.svg.

    Точка внимания стоит там же, где ее рисует MonochromeWithDot()
    в platform/win/tray_win.cpp, чтобы не расходиться с кодом трея."""
    svg = mark_svg('tray', {'plane': '#FFFFFF'}, background=False)
    if dot:
        klass, color = dot
        attr = f' class="{klass}"' if klass else ''
        svg = svg.replace(
            '</svg>',
            f'<circle{attr} fill="{color}" cx="3.9" cy="12.7" r="2.2"/></svg>')
    return svg


class Renderer:
    """Растеризация SVG headless-браузером на Chromium."""

    CANDIDATES = (
        r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
        r'C:\Program Files\Microsoft\Edge\Application\msedge.exe',
        r'C:\Program Files\Google\Chrome\Application\chrome.exe',
        r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
        '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
        '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',
        '/Applications/Chromium.app/Contents/MacOS/Chromium',
    )
    NAMES = ('chromium', 'chromium-browser', 'google-chrome',
             'google-chrome-stable', 'microsoft-edge', 'msedge', 'chrome')

    def __init__(self, browser=None):
        self.browser = browser or os.environ.get('NETGRAM_SVG_BROWSER')
        if not self.browser:
            found = [c for c in self.CANDIDATES if Path(c).exists()]
            found += [p for p in map(shutil.which, self.NAMES) if p]
            if not found:
                sys.exit('Не найден браузер на Chromium, укажите --browser.')
            self.browser = found[0]
        self.temp = Path(tempfile.mkdtemp(prefix='netgram_icons_'))

    def close(self):
        shutil.rmtree(self.temp, ignore_errors=True)

    def render_many(self, items):
        """items: [(svg_text_or_bytes, px)] -> [Image RGBA px x px]."""
        boxes = []
        left = 0
        for _, px in items:
            boxes.append((left, px))
            left += px + 8
        width = max(left, 256)
        height = max([px for _, px in items] + [256])
        tags = []
        for (svg, px), (x, _) in zip(items, boxes):
            data = svg.encode() if isinstance(svg, str) else svg
            b64 = base64.b64encode(data).decode()
            tags.append(
                f'<img src="data:image/svg+xml;base64,{b64}" style="position:'
                f'absolute;left:{x}px;top:0;width:{px}px;height:{px}px">')
        page = self.temp / 'page.html'
        shot = self.temp / 'shot.png'
        page.write_text(
            '<html><body style="margin:0;background:transparent">'
            + ''.join(tags) + '</body></html>', encoding='utf-8')
        if shot.exists():
            shot.unlink()
        subprocess.run([
            self.browser, '--headless=new', '--disable-gpu', '--no-first-run',
            '--force-device-scale-factor=1', '--hide-scrollbars',
            '--default-background-color=00000000',
            '--user-data-dir=' + str(self.temp / 'profile'),
            f'--window-size={width},{height}',
            '--screenshot=' + str(shot), page.as_uri(),
        ], capture_output=True, timeout=120)
        if not shot.exists():
            sys.exit('Браузер не сделал снимок: ' + self.browser)
        with Image.open(shot) as full:
            full = full.convert('RGBA')
            return [full.crop((x, 0, x + px, px)) for x, px in boxes]

    def render(self, svg, px):
        return self.render_many([(svg, px)])[0]


def kind_for(px):
    return 'tiny' if px <= 24 else 'small' if px <= 64 else 'big'


def write_ico(path, images):
    """ICO с PNG-кадрами, как 67.ico и прежний icon256.ico."""
    frames = []
    for image in sorted(images, key=lambda i: i.width):
        data = BytesIO()
        image.save(data, 'PNG', optimize=True)
        frames.append((image.width, data.getvalue()))
    header = struct.pack('<HHH', 0, 1, len(frames))
    offset = 6 + 16 * len(frames)
    entries = b''
    for side, data in frames:
        dim = 0 if side >= 256 else side
        entries += struct.pack('<BBBBHHII', dim, dim, 0, 0, 1, 32,
                               len(data), offset)
        offset += len(data)
    path.write_bytes(header + entries + b''.join(d for _, d in frames))


def write_text(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(text)


def save_png(image, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, 'PNG', optimize=True)


def placed(image, canvas, margin):
    result = Image.new('RGBA', (canvas, canvas), (0, 0, 0, 0))
    result.alpha_composite(image, (margin, margin))
    return result


def owner_png(px):
    path = HERE / 'png' / f'icon_{px}.png'
    return path if path.exists() else None


def build_main(renderer):
    big = (HERE / '67-app-icon.svg').read_bytes()

    def icon(px):
        path = owner_png(px)
        if path:
            with Image.open(path) as image:
                return image.convert('RGBA')
        return renderer.render(big, px)

    # Значки приложения - круг во весь размер, без полей.
    for base in (16, 32, 48, 64, 128, 256, 512):
        save_png(icon(base), ART / f'icon{base}.png')
        save_png(icon(base * 2), ART / f'icon{base}@2x.png')
    shutil.copyfile(HERE / '67.ico', ART / 'icon256.ico')

    # Поля повторяют исходные файлы tdesktop: logo_256.png (значок
    # для hicolor в Linux) - круг 228 с полями 14, logo_256_no_margin.png
    # (запасной аватар служебных уведомлений) - во весь размер,
    # icon_round512@2x.png (круглый значок в Dock) - круг 904 с полями 60.
    save_png(placed(renderer.render(big, 228), 256, 14), ART / 'logo_256.png')
    save_png(icon(256), ART / 'logo_256_no_margin.png')
    save_png(placed(renderer.render(big, 904), 1024, 60),
             ART / 'icon_round512@2x.png')
    save_png(placed(renderer.render(big, 912), 1024, 56), ART / 'icon_green.png')
    save_png(placed(renderer.render(big, 250), 256, 3), ART / 'iconbig_green.png')


def build_mac(renderer):
    mac = (HERE / '67-app-icon-macos.svg').read_bytes()
    sizes = (16, 32, 64, 128, 256, 512)
    rendered = dict(zip(sizes, renderer.render_many([(mac, s) for s in sizes])))
    with Image.open(HERE / 'png' / 'icon_macos_1024.png') as image:
        rendered[1024] = image.convert('RGBA')
    xcassets = MAC / 'Images.xcassets'
    for base in (16, 32, 128, 256, 512):
        save_png(rendered[base], xcassets / 'Icon.appiconset' / f'icon{base}.png')
        save_png(rendered[base * 2],
                 xcassets / 'Icon.appiconset' / f'icon{base}@2x.png')
        name = f'icon_{base}x{base}'
        save_png(rendered[base], xcassets / 'Icon.iconset' / f'{name}.png')
        save_png(rendered[base * 2], xcassets / 'Icon.iconset' / f'{name}@2x.png')

    layer = MAC / 'AppIcon-Default.icon' / 'Assets' / 'app.svg'
    write_text(layer, mark_svg('mac-layer', VARIANTS['default'], False))


def build_variants(renderer):
    for name, palette in VARIANTS.items():
        folder = ART / 'ayu' / name
        folder.mkdir(parents=True, exist_ok=True)
        svg = mark_svg('big', palette)
        if name != 'default':
            # Слой default для macOS свой (см. build_mac).
            write_text(MAC / f'AppIcon-{name.capitalize()}.icon' / 'Assets'
                       / 'app.svg', svg)
        write_text(folder / 'app.svg', svg)
        if name == 'default':
            shutil.copyfile(HERE / '67.ico', folder / 'app_icon.ico')
            continue
        frames = renderer.render_many(
            [(mark_svg(kind_for(px), palette), px) for px in ICO_SIZES])
        write_ico(folder / 'app_icon.ico', frames)


def hex_rgba(color):
    color = color.lstrip('#')
    return tuple(int(color[i:i + 2], 16) for i in (0, 2, 4)) + (255,)


def build_win95(renderer):
    """Пиксельный самолетик на бирюзовом круге в духе Windows 95."""
    def masks(kind, grid):
        side, (px, py, ps), digits = KINDS[kind]

        def layer(inner):
            return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{side}" '
                    f'height="{side}" viewBox="0 0 {side} {side}">'
                    f'<g transform="translate({px:g} {py:g}) scale({ps:g})">'
                    f'{inner}</g></svg>')
        wing = layer(f'<path fill="#fff" d="{PLANE[0]}"/>')
        body = layer(f'<path fill="#fff" d="{PLANE[1]}"/>')
        items = [(wing, grid), (body, grid)]
        if digits:
            dx, dy, ds = digits
            items.append((layer(
                f'<g transform="translate({dx:g} {dy:g}) scale({ds:g})" '
                f'fill="#fff"><path fill-rule="evenodd" d="{SIX}"/>'
                f'<path d="{SEVEN}"/></g>'), grid))
        result = []
        for image in renderer.render_many(items):
            alpha = image.getchannel('A')
            result.append({(x, y) for y in range(grid) for x in range(grid)
                           if alpha.getpixel((x, y)) >= 128})
        return result + [set()] * (3 - len(result))

    def pixel_art(px):
        grid = min(px, 64)
        kind = kind_for(grid)
        wing, body, digits = masks(kind, grid)
        plane = wing | body
        art = Image.new('RGBA', (grid, grid), (0, 0, 0, 0))
        for x, y in plane:
            shadow = (x + 1, y + 1)
            if shadow not in plane and shadow[0] < grid and shadow[1] < grid:
                art.putpixel(shadow, hex_rgba(WIN95['shadow']))
        for x, y in plane:
            if (x, y) in digits:
                color = WIN95['shadow']
            elif (x - 1, y) not in plane or (x, y - 1) not in plane:
                color = WIN95['light']
            else:
                color = WIN95['wing'] if (x, y) in wing else WIN95['body']
            art.putpixel((x, y), hex_rgba(color))
        art = art.resize((px, px), Image.NEAREST)
        circle = renderer.render(
            f'<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" '
            f'viewBox="0 0 64 64"><circle cx="32" cy="32" r="32" '
            f'fill="{WIN95["bg"]}"/></svg>', px)
        circle.alpha_composite(art)
        return circle

    folder = ART / 'ayu' / 'win95'
    folder.mkdir(parents=True, exist_ok=True)
    frames = [pixel_art(px) for px in ICO_SIZES]
    save_png(frames[-1], folder / 'app.png')
    save_png(frames[-1], MAC / 'AppIcon-Win95.icon' / 'Assets' / 'app.png')
    write_ico(folder / 'app_icon.ico', frames)


def build_tray(renderer):
    icons = RESOURCES / 'icons'
    files = {
        'tray_monochrome.svg': None,
        'tray_monochrome_attention.svg': ('error', '#f23c34'),
        'tray_monochrome_mute.svg': ('', '#888888'),
    }
    for name, dot in files.items():
        write_text(icons / name, tray_svg(dot))

    # st::macTrayIcon - обычная маска стилей: белое на черном.
    svg = mark_svg('mac-tray', {'plane': '#FFFFFF'}, background=False)
    scales = (('', 22), ('@2x', 44), ('@3x', 66))
    frames = renderer.render_many([(svg, px) for _, px in scales])
    for (suffix, _), frame in zip(scales, frames):
        alpha = frame.getchannel('A')
        save_png(Image.merge('RGB', (alpha, alpha, alpha)),
                 icons / f'mac_tray_icon{suffix}.png')


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--browser', help='путь к Edge/Chrome/Chromium')
    args = parser.parse_args()
    renderer = Renderer(args.browser)
    try:
        build_main(renderer)
        build_mac(renderer)
        build_variants(renderer)
        build_win95(renderer)
        build_tray(renderer)
    finally:
        renderer.close()
    print('Готово.')


if __name__ == '__main__':
    main()
