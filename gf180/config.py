"""Store configuration."""

__all__ = ["PATH"]

import pathlib

home = pathlib.Path.home()
cwd = pathlib.Path.cwd()
cwd_config = cwd / "config.yml"

home_config = home / ".config" / "gf180.yml"
config_dir = home / ".config"
config_dir.mkdir(exist_ok=True)
module_path = pathlib.Path(__file__).parent.absolute()
repo_path = module_path.parent


class Path:
    module = module_path
    repo = repo_path
    lyp = module_path / "klayout" / "tech" / "gf180mcu.lyp"
    lyp_yaml = module_path / "layers.yaml"


PATH = Path()

if __name__ == "__main__":
    print(PATH)
