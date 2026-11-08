"""Download the pinned sdialog/Primock-57 snapshot (CC BY 4.0) into data/raw/primock57."""
from huggingface_hub import snapshot_download

REVISION = "4bb215f61d97a3e4f209cdb45929bfa8a8e1cc32"

if __name__ == "__main__":
    path = snapshot_download("sdialog/Primock-57", repo_type="dataset", revision=REVISION,
                             allow_patterns=["data/*.json"], local_dir="data/raw/primock57_snapshot")
    print(path)
