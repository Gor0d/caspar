import hashlib
import re
from pathlib import Path
from fastapi import HTTPException

MAX_UPLOAD = 10 * 1024 * 1024
TEXT_EXTENSIONS = {'.txt', '.md', '.json', '.har', '.csv', '.log'}
EXTENSIONS = TEXT_EXTENSIONS | {'.png', '.jpg', '.jpeg', '.pdf'}


def validate_filename(name):
    if not name or len(name) > 200 or '/' in name or '\\' in name or ':' in name or any(ord(c) < 32 for c in name):
        raise HTTPException(422, 'Nome de arquivo inválido.')
    if Path(name).suffix.lower() not in EXTENSIONS:
        raise HTTPException(415, 'Formato não suportado. Use texto, JSON, HAR, CSV, PNG, JPEG ou PDF.')
    return name


def evidence_path(root, storage_name):
    if not re.fullmatch(r'[a-f0-9]{32}\.bin', storage_name):
        raise HTTPException(409, 'Referência de armazenamento inválida.')
    base = (root / 'evidence').resolve()
    path = base / storage_name
    if path.is_symlink() or path.resolve().parent != base:
        raise HTTPException(409, 'Arquivo fora do armazenamento permitido.')
    return path


def read_evidence(root, record):
    path = evidence_path(root, record.storage_name)
    if not path.is_file() or path.stat().st_size > MAX_UPLOAD:
        raise HTTPException(409, 'Evidência ausente ou inválida; restaure um backup.')
    content = path.read_bytes()
    if hashlib.sha256(content).hexdigest() != record.sha256:
        raise HTTPException(409, 'Falha de integridade da evidência (SHA-256).')
    return content
