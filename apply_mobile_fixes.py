#!/usr/bin/env python3
"""
Script para aplicar melhorias de responsividade mobile nos templates HTML
Executa todas as mudanças de uma vez em todos os templates
"""

import os
import re

TEMPLATES_DIR = "templates"

# 1. MEDIA QUERIES E ESTILOS BASE (adicionar antes de </style>)
MOBILE_STYLES = """
        /* ========== RESPONSIVE MOBILE FIXES ========== */
        
        /* Media Query: Tablet (1024px) */
        @media (max-width: 1024px) {
            .container {
                padding: 0 15px;
            }
            
            .content {
                gap: 20px;
            }
            
            .chart-container {
                height: 300px;
            }
            
            .header-nav {
                gap: 15px;
            }
        }
        
        /* Media Query: Tablet/Mobile (768px) */
        @media (max-width: 768px) {
            /* Header Hamburger Menu */
            .hamburger {
                display: block;
                background: none;
                border: none;
                color: white;
                font-size: 24px;
                cursor: pointer;
                padding: 0;
                width: 40px;
                height: 40px;
            }
            
            .hamburger:hover {
                opacity: 0.8;
            }
            
            .header-nav {
                display: none;
                position: fixed;
                left: 0;
                top: 60px;
                width: 100%;
                flex-direction: column;
                background: white;
                box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
                z-index: 999;
                padding: 10px 0;
                gap: 0;
            }
            
            .header-nav.active {
                display: flex;
            }
            
            .header-nav a {
                padding: 14px 20px;
                border-radius: 0;
                color: #333;
            }
            
            .header-nav a.logout {
                background: #f0f0f0;
            }
            
            .header-content {
                flex-wrap: wrap;
            }
            
            /* Layout responsivo - grids 1fr 2fr -> 1 coluna */
            .content {
                grid-template-columns: 1fr;
                gap: 15px;
            }
            
            /* Chart containers menores */
            .chart-container {
                height: 200px;
            }
            
            /* Circle de health score */
            .health-score-circle {
                width: 150px !important;
                height: 150px !important;
            }
            
            /* Grid de charts - 1 coluna */
            .chart-grid,
            .stats-grid {
                grid-template-columns: 1fr;
            }
            
            /* Touch targets maiores */
            input, button, select {
                min-height: 44px;
                padding: 12px 14px;
                font-size: 16px;
            }
            
            .delete-btn, .filter-btn, .action-btn {
                min-height: 44px;
                padding: 10px 14px;
            }
            
            /* Container padding */
            .container {
                padding: 0 10px;
            }
            
            /* Font sizing */
            label {
                font-size: 13px;
            }
            
            .subtitle {
                font-size: 12px;
            }
            
            .header-title {
                font-size: 20px;
            }
            
            h2 {
                font-size: 18px;
            }
            
            h3 {
                font-size: 16px;
            }
            
            /* Tabelas responsivas */
            table {
                font-size: 12px;
            }
            
            table td, table th {
                padding: 10px 8px;
            }
            
            .table-container {
                overflow-x: auto;
                -webkit-overflow-scrolling: touch;
            }
        }
        
        /* Media Query: Extra Small (480px) */
        @media (max-width: 480px) {
            .header-title {
                font-size: 18px;
            }
            
            h1 {
                font-size: 22px;
            }
            
            h2 {
                font-size: 16px;
            }
            
            .header-subtitle {
                font-size: 11px;
            }
            
            .container {
                padding: 0 8px;
            }
            
            input, button, select {
                min-height: 44px;
                font-size: 16px;
                padding: 12px 12px;
            }
            
            .chart-container {
                height: 180px;
            }
            
            .health-score-circle {
                width: 120px !important;
                height: 120px !important;
            }
            
            label {
                font-size: 12px;
            }
            
            table {
                font-size: 11px;
            }
            
            table td, table th {
                padding: 8px 4px;
            }
        }
"""

# 2. SCRIPT PARA HAMBURGER MENU
HAMBURGER_SCRIPT = """
        // Hamburger Menu Toggle
        function toggleMenu() {
            const nav = document.querySelector('.header-nav');
            if (nav) {
                nav.classList.toggle('active');
            }
        }
        
        // Fechar menu quando clicar em um link
        document.querySelectorAll('.header-nav a').forEach(link => {
            link.addEventListener('click', () => {
                const nav = document.querySelector('.header-nav');
                if (nav) {
                    nav.classList.remove('active');
                }
            });
        });
"""

def cleanup_template(html_content):
    """Remove comentários antigos ou blocos vazios de proteção."""
    html_content = re.sub(r'/\* Disable text selection and copying \*/\s*\*\s*\{\s*\}\s*', '', html_content, flags=re.IGNORECASE)
    html_content = re.sub(r'/\* Disable right-click context menu \*/\s*body\s*\{\s*\}\s*', '', html_content, flags=re.IGNORECASE)
    html_content = re.sub(r'/\* Allow text selection in form inputs \*/\s*input, textarea, select\s*\{\s*-[^}]*\}\s*', lambda m: m.group(0), html_content, flags=re.IGNORECASE)
    return html_content


def add_hamburger_button(html_content):
    """Adiciona botão hambúrguer ao header se não existir"""
    if 'class="hamburger"' in html_content:
        return html_content

    pattern = r'(<div class="header-content">.*?)(<(?:div|nav) class="header-nav")'
    replacement = r'\1<button class="hamburger" onclick="toggleMenu()">☰</button>\n        \2'
    result = re.sub(pattern, replacement, html_content, flags=re.DOTALL)

    if result == html_content:
        result = re.sub(r'(<(?:div|nav) class="header-nav")', r'<button class="hamburger" onclick="toggleMenu()">☰</button>\n        \1', html_content, flags=re.DOTALL)

    return result


def add_mobile_styles(html_content):
    """Adiciona media queries antes de </style>"""
    if 'RESPONSIVE MOBILE FIXES' in html_content:
        return html_content

    return html_content.replace('        </style>', MOBILE_STYLES + '\n        </style>')


def add_hamburger_script(html_content):
    """Adiciona script de hamburger antes de </body>"""
    if 'toggleMenu' in html_content:
        return html_content

    if '</body>' in html_content:
        return html_content.replace('</body>', f'    <script>{HAMBURGER_SCRIPT}\n    </script>\n</body>')
    elif '</script>' in html_content:
        last_script = html_content.rfind('</script>')
        return html_content[:last_script+9] + f'\n    <script>{HAMBURGER_SCRIPT}\n    </script>' + html_content[last_script+9:]

    return html_content

def process_template(filepath):
    """Processa um arquivo de template"""
    print(f"  Processando {os.path.basename(filepath)}...")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Aplicar melhorias
    content = cleanup_template(content)
    content = add_hamburger_button(content)
    content = add_mobile_styles(content)
    content = add_hamburger_script(content)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"  ✓ {os.path.basename(filepath)} atualizado!")

def main():
    print("=" * 60)
    print("APLICANDO MELHORIAS DE RESPONSIVIDADE MOBILE")
    print("=" * 60)
    
    if not os.path.isdir(TEMPLATES_DIR):
        print(f"❌ Erro: Pasta '{TEMPLATES_DIR}' não encontrada!")
        return
    
    template_files = [
        f for f in os.listdir(TEMPLATES_DIR) 
        if f.endswith('.html')
    ]
    
    print(f"\nEncontrados {len(template_files)} templates\n")
    
    for template_file in sorted(template_files):
        filepath = os.path.join(TEMPLATES_DIR, template_file)
        try:
            process_template(filepath)
        except Exception as e:
            print(f"  ❌ Erro ao processar {template_file}: {e}")
    
    print("\n" + "=" * 60)
    print("✓ MELHORIAS APLICADAS COM SUCESSO!")
    print("=" * 60)
    print("\nMudanças realizadas:")
    print("  ✓ Hamburger menu adicionado (mobile)")
    print("  ✓ Media queries responsivas (768px, 480px)")
    print("  ✓ Layouts grid adaptáveis")
    print("  ✓ Chart containers responsivos")
    print("  ✓ Touch targets aumentados (44px)")
    print("  ✓ Font sizes escaláveis")

if __name__ == "__main__":
    main()
