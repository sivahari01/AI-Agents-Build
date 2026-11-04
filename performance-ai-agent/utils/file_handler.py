import shutil
from pathlib import Path


def save_upload(uploaded_file, destination_dir: str | Path) -> Path:
    destination_dir = Path(destination_dir)
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / uploaded_file.name
    with destination.open("wb") as output:
        shutil.copyfileobj(uploaded_file, output)
    return destination
