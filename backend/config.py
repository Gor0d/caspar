import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(REPO / '.env'), extra='ignore')
    caspar_data_dir: Path = Path.home() / '.caspar'
    openai_api_key: str = ''
    openai_model: str = ''
    ollama_model: str = ''
    ollama_port: int = 11434
    ai_input_cost_per_million: float = 0
    ai_output_cost_per_million: float = 0

    def prepare(self):
        root = self.caspar_data_dir.expanduser().resolve()
        if root == REPO or REPO in root.parents or root == Path.home().resolve() or root == Path(root.anchor):
            raise ValueError('CASPAR_DATA_DIR must be a dedicated directory outside the repository.')
        if not 1 <= self.ollama_port <= 65535:
            raise ValueError('Invalid Ollama port')
        self.caspar_data_dir = root
        for path in (root, root / 'evidence', root / 'reports', root / 'backups'):
            if path.is_symlink() or (hasattr(path, 'is_junction') and path.is_junction()):
                raise ValueError('Storage subdirectories cannot be symbolic links or junctions.')
            path.mkdir(parents=True, exist_ok=True, mode=0o700)
            if os.name != 'nt':
                path.chmod(0o700)
        return self
