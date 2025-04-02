import re
from argparse import ArgumentParser
from hashlib import md5
from pathlib import Path

FILESIZE_THRESHOLD = 2 * 1000 * 1000

GOPRO_REGEXP_LIST = [
    re.compile(r, re.I)
    for r in [
        r"(?P<hdr>G[HXL])(?P<chp>[0-9]{2})(?P<num>[0-9]{4})\.(?P<ext>lrv|mp4)$",
        r"(?P<hdr>G[HXL])_(?P<num>[0-9]{4})_(?P<chp>[0-9]{2})\.(?P<ext>lrv|mp4)$",
        r"(?P<num>[0-9]{4})-(?P<chp>[0-9]{2})_(?P<hdr>G[HXL])\.(?P<ext>lrv|mp4)$",
    ]
]


def run():
    renamer = Renamer()
    renamer.rename_all()


class Renamer:
    def __init__(self):
        self._dir_cache = {}
        parser = ArgumentParser()
        parser.add_argument("-v", "--verbose", action="store_true")
        parser.add_argument("-y", "--yes", action="store_true")
        parser.add_argument("paths", type=Path, nargs="*")
        self.args = parser.parse_args()

    def rename_all(self):
        for path in (p.resolve() for p in self.args.paths):
            if path.is_dir():
                for origin in path.iterdir():
                    self.rename_lrv(origin)
            elif path.is_file():
                self.rename_lrv(path)

    def rename_lrv(self, origin: Path):
        if lrv := self.find_lrv(origin):
            self.log(f"Found LRV for {origin}: {lrv}. Calculating hash ...", end="")
            file_hash = calculate_hash(origin)
            self.log(f"done: {file_hash}")
            proxy = origin.parent / "cachefiles" / "proxy" / f"{file_hash}.mov"
            if self.args.yes or input(f"Move {lrv} to {proxy} (y/n)? ") == "y":
                self.log(f"Moving {lrv} to {proxy} ...", end="")
                proxy.parent.mkdir(parents=True, exist_ok=True)
                lrv.rename(proxy)
                self.log("done")
        else:
            self.log(f"{origin} has no LRV file")

    def find_lrv(self, origin: Path) -> Path | None:
        try:
            ext, _, number, chapter = match_gopro_file(origin.name)
            if ext != "mp4":
                raise TypeError
        except TypeError:
            self.log(f"Skipping not a GoPro video file {origin}")
            return None

        directory = origin.resolve().parent
        if directory in self._dir_cache:
            siblings = self._dir_cache[directory]
        else:
            siblings = {}
            for f in directory.iterdir():
                if not (m := match_gopro_file(f.name)):
                    continue
                siblings[m] = f
            self._dir_cache[directory] = siblings

        return siblings.get(("lrv", "gl", number, chapter))

    def log(self, *args, **kwargs):
        if self.args.verbose:
            print(*args, **kwargs)


def match_gopro_file(filename: str) -> tuple | None:
    for regex in GOPRO_REGEXP_LIST:
        if m := regex.match(filename):
            return tuple(m.group(g).lower() for g in ("ext", "hdr", "num", "chp"))


def calculate_hash(filepath: Path) -> str:
    with filepath.open("rb") as f:
        filesize = filepath.stat().st_size

        if filesize > FILESIZE_THRESHOLD:
            data = f.read(FILESIZE_THRESHOLD >> 1)
            f.seek(filesize - (FILESIZE_THRESHOLD >> 1))
            data += f.read(FILESIZE_THRESHOLD >> 1)
        else:
            data = f.read()

    return md5(data).hexdigest()
