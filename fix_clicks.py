import os
import re

TEMPLATES_DIR = "templates"

def remove_problematic_css(html_content):
    # Remove linhas CSS problemáticas que bloqueiam cliques
    html_content = re.sub(r'.*pointer-events:\s*none;.*\n?', '', html_content, flags=re.IGNORECASE)
    html_content = re.sub(r'.*user-select:\s*none;.*\n?', '', html_content, flags=re.IGNORECASE)
    return html_content

def process_template(filepath):
    print(f"Processando {os.path.basename(filepath)}...")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    content = remove_problematic_css(content)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✓ {os.path.basename(filepath)} atualizado!")

def main():
    if not os.path.isdir(TEMPLATES_DIR):
        print(f"Erro: Pasta '{TEMPLATES_DIR}' não encontrada!")
        return
    
    template_files = [f for f in os.listdir(TEMPLATES_DIR) if f.endswith('.html')]
    
    for template_file in sorted(template_files):
        filepath = os.path.join(TEMPLATES_DIR, template_file)
        try:
            process_template(filepath)
        except Exception as e:
            print(f"Erro ao processar {template_file}: {e}")
    
    print("Remoção de linhas CSS problemáticas concluída!")

if __name__ == "__main__":
    main()
