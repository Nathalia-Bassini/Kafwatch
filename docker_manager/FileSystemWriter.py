import yaml
import os
from pathlib import Path

class FileSystemWriter:
    """
    (S)RP: Tem a única responsabilidade de escrever 
    ficheiros de configuração no disco.
    """
    def __init__(self, base_path: str | Path = '.'):
        self.base_path = Path(base_path)

    def _ensure_dir_exists(self, file_path: Path):
        """Helper privado para garantir que o diretório pai existe."""
        file_path.parent.mkdir(parents=True, exist_ok=True)

    def write_yaml(self, file_name: str, data: dict):
        """Escreve um dicionário como um ficheiro YAML."""
        full_path = self.base_path / file_name
        self._ensure_dir_exists(full_path)
        
        try:
            with open(full_path, 'w') as f:
                yaml.dump(data, f, default_flow_style=False, sort_keys=False)
            print(f"Arquivo YAML gerado: {full_path.resolve()}")
        except Exception as e:
            print(f"Erro ao salvar {full_path}: {e}")

    def write_lines(self, file_name: str, lines: list[str]):
        """Escreve uma lista de linhas num ficheiro de texto."""
        full_path = self.base_path / file_name
        self._ensure_dir_exists(full_path)
        
        try:
            with open(full_path, 'w') as f:
                f.writelines(lines)
            print(f"Arquivo de texto gerado: {full_path.resolve()}")
        except Exception as e:
            print(f"Erro ao salvar {full_path}: {e}")

    @staticmethod
    def load_template(template_path: str) -> list[str]:
        """Método estático para carregar um ficheiro de template."""
        try:
            with open(template_path, 'r') as f:
                return f.readlines()
        except Exception as e:
            print(f"Erro ao carregar template {template_path}: {e}")
            return []