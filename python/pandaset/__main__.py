
import argparse
import os
import sys
from pathlib import Path
from zipfile import ZipFile

_ACTION_MERGE_LIDAR_RAW = "merge_lidar_raw"

def parse_args():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(title="actions", dest="action")
    subparsers.required = True

    lidar_raw_parser = subparsers.add_parser(_ACTION_MERGE_LIDAR_RAW)
    lidar_raw_parser.add_argument(
        "data_dir",
        type=str,
        help="Path to PandaSet data directory"
    )
    lidar_raw_parser.add_argument(
        "lidar_raw_data_zip",
        type=str,
        help="Path to pandar64_raw_data.zip"
    )

    args = parser.parse_args()
    if args.action == _ACTION_MERGE_LIDAR_RAW:
        if not Path(args.data_dir).exists():
            print(args.data_dir, "does not exist.")
            sys.exit(1)
        if not Path(args.lidar_raw_data_zip).exists():
            print(args.lidar_raw_data_zip, "does not exist.")
            sys.exit(1)

    return args

def main():
    args = parse_args()
    data_dir = Path(args.data_dir).resolve()
    sequence_dirs = list(filter(
        lambda p: p.is_dir(),
        data_dir.iterdir()
    ))

    sequence_ids = set(map(lambda seq: seq.name, sequence_dirs))

    exist = set()
    with ZipFile(args.lidar_raw_data_zip, "r") as zip_file:
        lidar_raw_file_paths = list(filter(
            lambda p: Path(p).parent.name in sequence_ids,
            zip_file.namelist()
        ))

        for lidar_raw_file_path in lidar_raw_file_paths:
            sequence_id = Path(lidar_raw_file_path).parent.name
            lidar_dir = data_dir / sequence_id / "lidar"
            lidar_raw_dir = data_dir / sequence_id / "lidar_raw"
            lidar_raw_dir.mkdir(mode=0o700, exist_ok=True)

            with zip_file.open(lidar_raw_file_path, "r") as f:
                content = f.read()
            with (lidar_raw_dir / Path(lidar_raw_file_path).name).open("wb") as f_:
                f_.write(content)

            poses_filename = "poses.json"
            poses_src = lidar_dir / poses_filename
            poses_dst = lidar_raw_dir / poses_filename
            if poses_dst not in exist:
                os.symlink(poses_src, poses_dst)
                exist.add(poses_dst)

            timestamps_filename = "timestamps.json"
            timestamps_src = lidar_dir / timestamps_filename
            timestamps_dst = lidar_raw_dir / timestamps_filename
            if timestamps_dst not in exist:
                os.symlink(timestamps_src, timestamps_dst)
                exist.add(timestamps_dst)

    print(len(lidar_raw_file_paths), "raw LiDAR scans merged.")


if __name__ == "__main__":
    main()
