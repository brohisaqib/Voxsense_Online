from pathlib import Path
import os
from loguru import logger


class FileManager:
    async def open_file(self, name: str) -> str:
        dirs = [Path.home()/"Desktop", Path.home()/"Documents", Path.home()/"Downloads"]
        for d in dirs:
            matches = list(d.glob(f"*{name}*"))
            if matches:
                os.startfile(str(matches[0]))
                return f"Opened {matches[0].name}"
        return f"File {name} not found."

    async def search_file(self, name: str) -> str:
        dirs = [Path.home()/"Desktop", Path.home()/"Documents", Path.home()/"Downloads"]
        found = []
        for d in dirs:
            found.extend([f.name for f in d.glob(f"*{name}*")])
        return f"Found: {', '.join(found)}" if found else f"No files matching {name}."

    async def list_folder(self, folder: str) -> str:
        try:
            paths = {
                "desktop": Path.home()/"Desktop",
                "documents": Path.home()/"Documents",
                "downloads": Path.home()/"Downloads"
            }
            p = paths.get(folder.lower(), Path(folder))
            files = [f.name for f in p.iterdir()][:15]
            return f"{folder}: {', '.join(files)}" if files else "Empty folder."
        except Exception as e:
            return f"Could not list folder. {e}"

    async def create_folder(self, path: str) -> str:
        try:
            Path(path).mkdir(parents=True, exist_ok=True)
            return f"Folder created: {path}"
        except Exception as e:
            return f"Could not create folder. {e}"