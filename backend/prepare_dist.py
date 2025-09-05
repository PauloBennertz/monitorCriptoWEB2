import os
import shutil
import sys

def prepare_dist():
    """Prepares the dist folder with all the necessary files."""

    print("Preparando pasta de distribuicao...")

    # Criar pasta dist se não existir
    if not os.path.exists('dist'):
        os.makedirs('dist')

    # Arquivos e pastas para copiar
    files_to_copy = [
        ('config.json', 'dist/'),
        ('icons', 'dist/'),
        ('sons', 'dist/'),
    ]

    # Copiar arquivos
    for src, dst in files_to_copy:
        try:
            if os.path.isdir(src):
                if os.path.exists(dst + os.path.basename(src)):
                    shutil.rmtree(dst + os.path.basename(src))
                shutil.copytree(src, dst + os.path.basename(src))
                print(f"Pasta copiada: {src} -> {dst}")
            else:
                shutil.copy2(src, dst)
                print(f"Arquivo copiado: {src} -> {dst}")
        except Exception as e:
            print(f"Erro ao copiar {src}: {e}")

    # Criar arquivo de instruções
    instructions = """# Monitor de Criptomoedas

## Como Executar

1. **Execute o arquivo**: `MonitorCriptomoedas.exe`
2. **Primeira execução**: O programa criará as configurações automaticamente
3. **Configurar alertas**: Use o menu "Configurações" para personalizar

## Arquivos Incluídos

- `MonitorCriptomoedas.exe` - Programa principal
- `config.json` - Configurações
- `icons/` - Ícones da interface
- `sons/` - Arquivos de som para alertas

## Requisitos

- Windows 10 ou superior
- Conexão com internet
- 4GB RAM mínimo

## Suporte

Se houver problemas:
1. Execute como administrador
2. Verifique o antivírus
3. Verifique a conexão com internet

**Pronto para usar!**
"""

    with open('dist/LEIA-ME.txt', 'w', encoding='utf-8') as f:
        f.write(instructions)

    print("Pasta dist preparada com sucesso!")
    print("Arquivos na pasta dist:")

    # Listar arquivos na pasta dist
    for item in os.listdir('dist'):
        path = os.path.join('dist', item)
        if os.path.isfile(path):
            size = os.path.getsize(path) / (1024 * 1024)  # MB
            print(f"   {item} ({size:.1f} MB)")
        else:
            print(f"   {item}/")

if __name__ == "__main__":
    prepare_dist()