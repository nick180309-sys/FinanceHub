import os
import re

TEMPLATES_DIR = "templates"

RESPONSIVE_CSS = """
        /* ==== MOBILE RESPONSIVE FIXES ==== */
        .hamburger {
            display: none;
            background: none;
            border: none;
            color: white;
            font-size: 24px;
            cursor: pointer;
            padding: 0;
            width: 42px;
            height: 42px;
        }

        .hamburger:hover {
            opacity: 0.85;
        }

        .header-nav.active {
            display: flex;
        }

        @media (max-width: 1024px) {
            .container {
                padding: 0 16px;
            }

            .content {
                gap: 20px;
            }

            .chart-container {
                height: 300px;
            }
        }

        @media (max-width: 768px) {
            .hamburger {
                display: block;
            }

            .header-content {
                flex-wrap: wrap;
                gap: 10px;
            }

            .header-nav {
                display: none;
                position: fixed;
                top: 72px;
                left: 0;
                right: 0;
                width: 100%;
                background: white;
                flex-direction: column;
                padding: 10px 0;
                gap: 0;
                box-shadow: 0 10px 30px rgba(0, 0, 0, 0.12);
                z-index: 999;
                border-top: 1px solid rgba(0, 0, 0, 0.08);
            }

            .header-nav a {
                color: #333;
                padding: 14px 20px;
                border-radius: 0;
                display: block;
                width: 100%;
            }

            .header-nav a:hover, .header-nav a.active {
                background: rgba(102, 126, 234, 0.08);
                color: #222;
            }

            .header-nav .logout {
                background: #f4f4f4;
            }

            .content {
                grid-template-columns: 1fr !important;
                gap: 18px;
            }

            .chart-container {
                height: 220px;
            }

            .chart-grid,
            .stats-grid,
            .cards-grid {
                grid-template-columns: 1fr !important;
            }

            input, button, select {
                min-height: 44px;
                padding: 12px 14px;
                font-size: 15px;
            }

            .container {
                padding: 0 12px;
            }

            label {
                font-size: 13px;
            }

            .subtitle {
                font-size: 12px;
            }

            .header-title {
                font-size: 20px;
            }

            h1 {
                font-size: 24px;
            }

            h2 {
                font-size: 18px;
            }
        }

        @media (max-width: 480px) {
            .container {
                padding: 0 10px;
            }

            .header-title {
                font-size: 18px;
            }

            h1 {
                font-size: 22px;
            }

            h2 {
                font-size: 16px;
            }

            .chart-container {
                height: 180px;
            }

            table {
                font-size: 11px;
            }

            table td, table th {
                padding: 8px 4px;
            }
        }
"""

HAMBURGER_SCRIPT = """
        <script>
            function toggleMenu() {
                const nav = document.querySelector('.header-nav');
                if (nav) {
                    nav.classList.toggle('active');
                }
            }

            document.querySelectorAll('.header-nav a').forEach(link => {
                link.addEventListener('click', () => {
                    const nav = document.querySelector('.header-nav');
                    if (nav) {
                        nav.classList.remove('active');
                    }
                });
            });
        </script>
"""

HAMBURGER_BUTTON = '<button class="hamburger" onclick="toggleMenu()">☰</button>'


def cleanup_css(content):
    content = re.sub(r'.*user-select:\s*none;.*\n?', '', content, flags=re.IGNORECASE)
    content = re.sub(r'.*-webkit-touch-callout:\s*none;.*\n?', '', content, flags=re.IGNORECASE)
    content = re.sub(r'.*pointer-events:\s*none;.*\n?', '', content, flags=re.IGNORECASE)
    content = re.sub(r'oncontextmenu="return false;"', '', content, flags=re.IGNORECASE)
    content = re.sub(r'onselectstart="return false;"', '', content, flags=re.IGNORECASE)
    content = re.sub(r'onkeydown="return disableCtrl\(event\);"', '', content, flags=re.IGNORECASE)
    content = re.sub(r'document\.addEventListener\(\s*[\'\"]contextmenu[\'\"]\s*,.*?\);', '', content, flags=re.IGNORECASE | re.DOTALL)
    content = re.sub(r'document\.body\.oncontextmenu\s*=\s*.*?;', '', content, flags=re.IGNORECASE)
    content = re.sub(r'window\.oncontextmenu\s*=\s*.*?;', '', content, flags=re.IGNORECASE)
    content = re.sub(r'function disableCtrl\(event\).*?\n\s*\}', '', content, flags=re.IGNORECASE | re.DOTALL)
    content = re.sub(r'document\.addEventListener\(\s*[\'\"]keydown[\'\"]\s*,.*?\n\s*\}\);', '', content, flags=re.IGNORECASE | re.DOTALL)
    content = re.sub(r'document\.onkeydown\s*=\s*.*?;', '', content, flags=re.IGNORECASE)
    content = re.sub(r'window\.onkeydown\s*=\s*.*?;', '', content, flags=re.IGNORECASE)
    content = re.sub(r'<script>.*?(?:Disable common copy shortcuts|Disable F12|Disable right-click|Re-enable right-click).*?</script>', '', content, flags=re.IGNORECASE | re.DOTALL)
    content = re.sub(r'<script>\s*</script>', '', content, flags=re.IGNORECASE)
    return content


def add_hamburger(html_content):
    if 'class="hamburger"' in html_content:
        return html_content
    pattern = r'(<div class="header-content">.*?)(<div class="header-nav")'
    replacement = r'\1' + HAMBURGER_BUTTON + r'\n        \2'
    result = re.sub(pattern, replacement, html_content, flags=re.DOTALL)
    if result == html_content:
        result = re.sub(r'(<div class="header-nav")', HAMBURGER_BUTTON + r'\n        \1', html_content, flags=re.DOTALL)
    return result


def add_responsive_css(html_content):
    if '/* ==== MOBILE RESPONSIVE FIXES ==== */' in html_content:
        return html_content
    if '</style>' in html_content:
        return html_content.replace('</style>', RESPONSIVE_CSS + '\n        </style>')
    return html_content


def add_hamburger_script(html_content):
    if 'function toggleMenu' in html_content:
        return html_content
    if '</body>' in html_content:
        return html_content.replace('</body>', HAMBURGER_SCRIPT + '\n</body>')
    return html_content


def process_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    content = cleanup_css(content)
    content = add_hamburger(content)
    content = add_responsive_css(content)
    content = add_hamburger_script(content)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"Updated: {filepath}")


def main():
    if not os.path.isdir(TEMPLATES_DIR):
        print(f"Templates folder not found: {TEMPLATES_DIR}")
        return

    for filename in sorted(os.listdir(TEMPLATES_DIR)):
        if filename.endswith('.html'):
            process_file(os.path.join(TEMPLATES_DIR, filename))

    print('All templates updated.')


if __name__ == '__main__':
    main()
