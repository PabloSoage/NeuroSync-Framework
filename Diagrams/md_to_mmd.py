import os
def process_mermaid_files(directory="."):
    for filename in os.listdir(directory):
        if filename.endswith('.md'):
            md_path = os.path.join(directory, filename)
            mmd_path = os.path.join(directory, filename.replace('.md', '.mmd'))
            with open(md_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            if len(lines) > 2:
                new_lines = lines[1:-1]
            else:
                new_lines = []
            with open(mmd_path, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            os.remove(md_path)
            print(f"Procesado: {md_path} → {mmd_path} (eliminado original)")

process_mermaid_files(".")