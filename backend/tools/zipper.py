import shutil
from pathlib import Path


def zip_pasta(origem: Path, destino_sem_extensao: Path) -> Path:
    caminho = shutil.make_archive(str(destino_sem_extensao), "zip", root_dir=origem)
    return Path(caminho)
