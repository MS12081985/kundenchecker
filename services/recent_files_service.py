"""Management of the small, persisted Excel file history."""

from pathlib import Path


class RecentFilesService:
    MAX_FILES = 5

    @classmethod
    def clean(cls, values):
        result = []
        for value in values or ():
            path = Path(str(value)).expanduser()
            normalized = str(path.resolve())
            if path.is_file() and normalized not in result:
                result.append(normalized)
            if len(result) == cls.MAX_FILES:
                break
        return result

    @classmethod
    def add(cls, values, filename):
        path = Path(filename).expanduser()
        normalized = str(path.resolve())
        return cls.clean([normalized, *(values or ())])
