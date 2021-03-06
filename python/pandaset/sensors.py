#!/usr/bin/env python3
import glob
import json
import os.path
from typing import List, overload, TypeVar, Dict
from abc import ABCMeta, abstractmethod

import numpy as np
import pandas as pd
from PIL import Image
from PIL.JpegImagePlugin import JpegImageFile
from pandas.core.frame import DataFrame

T = TypeVar('T')


class Sensor:
    """Meta class inherited by subclasses for more specific sensor types.

   ``Sensor`` provides generic preparation and loading methods for PandaSet folder structures. Subclasses
   for specific sensor types must implement certain methods, as well as can override existing ones for extension.

   Args:
        directory: Absolute or relative path where sensor files are stored

   Attributes:
       data: List of sensor data objects. The type of list elements depends on the subclass implementation of protected method ``_load_data_file``
       poses: List of sensor poses in world-coordinates
       timestamps: List of recording timestamps for sensor
   """
    __metaclass__ = ABCMeta

    @property
    @abstractmethod
    def _data_file_extension(self) -> str:
        ...

    @property
    def data(self) -> List[T]:
        """Returns sensor data array.

        Subclasses can use any type inside array.
        """
        return self._data

    @property
    def poses(self) -> List[T]:
        """Returns sensor pose array.

        Subclasses can use any type inside array.
        """
        return self._poses

    @property
    def timestamps(self) -> List[T]:
        """Returns sensor timestamp array.

        Subclasses can use any type inside array.
        """
        return self._timestamps

    def __init__(self, directory: str) -> None:
        self._directory: str = directory
        self._data_structure: List[str] = None
        self._data: List[T] = None
        self._poses_structure: str = None
        self._poses: List[Dict[str, T]] = None
        self._timestamps_structure: str = None
        self._timestamps: List[float] = None
        self._load_structure()

    @overload
    def __getitem__(self, item: int) -> T:
        ...

    @overload
    def __getitem__(self, item: slice) -> List[T]:
        ...

    def __getitem__(self, item):
        return self.data[item]

    def _load_structure(self) -> None:
        self._load_data_structure()
        self._load_poses_structure()
        self._load_timestamps_structure()

    def _load_data_structure(self) -> None:
        self._data_structure = sorted(
            glob.glob(f'{self._directory}/*.{self._data_file_extension}'))

    def _load_poses_structure(self) -> None:
        poses_file = f'{self._directory}/poses.json'
        if os.path.isfile(poses_file):
            self._poses_structure = poses_file

    def _load_timestamps_structure(self) -> None:
        timestamps_file = f'{self._directory}/timestamps.json'
        if os.path.isfile(timestamps_file):
            self._timestamps_structure = timestamps_file

    def load(self) -> None:
        """Loads all sensor files from disk into memory.

        All sensor and associated meta data files are loaded into memory in filename order.
        """
        self._load_data()
        self._load_poses()
        self._load_timestamps()

    def load_single(self, index, clear_data=True) -> None:
        """Loads a single sensor file from disk into memory while others
        are set to an empty data frame.

        All sensor and associated meta data files are traversed in filename order.
        """
        self._load_single_data_item(index, clear_data)
        self._load_single_pose(index, clear_data)
        self._load_single_timestamp(index, clear_data)

    def unload_single(self, index) -> None:
        """Unloads a single sensor file from memory.
        """
        self._unload_single_data_item(index)
        self._unload_single_pose(index)
        self._unload_single_timestamp(index)

    def _load_data(self) -> None:
        self._data = []
        for fp in self._data_structure:
            self._data.append(self._load_data_file(fp))

    def _load_single_data_item(self, index, clear_data):
        if clear_data:
            # Dummy data frame
            self._data = [pd.DataFrame(columns=["d"])] * len(self._data_structure)

        fp = self._data_structure[index]
        self._data[index] = self._load_data_file(fp)

    def _unload_single_data_item(self, index):
        self._data[index] = pd.DataFrame(columns=["d"])

    def _load_poses(self) -> None:
        self._poses = []
        with open(self._poses_structure, 'r') as f:
            file_data = json.load(f)
            for entry in file_data:
                self._poses.append(entry)

    def _load_single_pose(self, index, clear_data):
        with open(self._poses_structure, 'r') as f:
            file_data = json.load(f)
            if clear_data:
                self._poses = [None] * len(file_data)

            entry = file_data[index]
            self._poses[index] = entry

    def _unload_single_pose(self, index):
        self._poses[index] = None

    def _load_timestamps(self) -> None:
        self._timestamps = []
        with open(self._timestamps_structure, 'r') as f:
            file_data = json.load(f)
            for entry in file_data:
                self._timestamps.append(entry)

    def _load_single_timestamp(self, index, clear_data) -> None:
        with open(self._timestamps_structure, 'r') as f:
            file_data = json.load(f)
            if clear_data:
                self._timestamps = [None] * len(file_data)

            entry = file_data[index]
            self._timestamps[index] = entry

    def _unload_single_timestamp(self, index):
        self._timestamps[index] = None

    @abstractmethod
    def _load_data_file(self, fp: str) -> None:
        ...


class Lidar(Sensor):
    @property
    def _data_file_extension(self) -> str:
        return 'pkl.gz'

    @property
    def data(self) -> List[pd.DataFrame]:
        """Returns (filtered) LiDAR point cloud array.

        Point cloud data is in a world-coordinate system, i.e., a static object which is a position `(10,10,0)` in frame 1, will be at position `(10,10,0)` in all other frames, too.

        Returns:
            List of point cloud data frames for each timestamp. Each data frame has columns as follows:
                - index: `int`
                    - Ordered point cloud. When joining the raw point cloud with data from ``SemanticSegmentation``, it is important to keep the index order.
                - `x`: `float`
                    - Position of point in world-coordinate system (x-axis) in meter
                - `y`: `float`
                    - Position of point in world-coordinate system (y-axis) in meter
                - `z`: `float`
                    - Position of point in world-coordinate system (z-axis) in meter
                - `i`: `float`
                    - Reflection intensity in a range `[0,255]`
                - `t`: `float`
                    - Recorded timestamp for specific point
                - `d`: `int`
                    - Sensor ID. `0` -> mechnical 360° LiDAR, `1` -> forward-facing LiDAR
        """
        if self._sensor_id in [0, 1]:
            return [df.loc[df['d'] == self._sensor_id] for df in self._data]
        else:
            return self._data

    @property
    def poses(self) -> List[Dict[str, Dict[str, float]]]:
        """Returns LiDAR sensor pose array.

        Returns:
            A pose dictionary of the LiDAR sensor in world-coordinates for each frame. The dictionary keys return the following types:
             - `position`: `dict`
                - `x`: `float`
                    - Position of LiDAR sensor in world-coordinate system (x-axis) in meter
                - `y`: `float`
                    - Position of LiDAR sensor in world-coordinate system (y-axis) in meter
                - `z`: `float`
                    - Position of LiDAR sensor in world-coordinate system (z-axis) in meter
            - `heading`: `dict`
                - `w`: `float`
                    - Real part of _Quaternion_
                - `x`: `float`
                    - First imaginary part of _Quaternion_
                - `y`: `float`
                    - Second imaginary part of _Quaternion_
                - `z`: `float`
                    - Third imaginary part of _Quaternion_
        """
        return self._poses

    @property
    def timestamps(self) -> List[float]:
        """Returns LiDAR sensor recording timestamps array.

        Returns:
            A list of timestamps in `float` format for each point cloud recorded in this sequence. To get point-wise timestamps, please refer to column `t` in `data` property return values.
        """
        return self._timestamps

    def __init__(self, directory: str) -> None:
        self._sensor_id = -1
        Sensor.__init__(self, directory)

    @overload
    def __getitem__(self, item: int) -> DataFrame:
        ...

    @overload
    def __getitem__(self, item: slice) -> List[DataFrame]:
        ...

    def __getitem__(self, item):
        return super().__getitem__(item)

    def set_sensor(self, sensor_id: int) -> None:
        """Specifies a sensor which should be returned exclusively in the data objects

        Args:
            sensor_id: Set `-1` for both LiDAR sensors, set `0` for mechanical 360° LiDAR, set `1` for front-facing LiDAR.

        """
        self._sensor_id = sensor_id

    def _load_data_file(self, fp: str) -> DataFrame:
        return pd.read_pickle(fp)


class LidarRaw(Lidar):
    # 360 mechanical LiDAR

    def __init__(self, directory: str) -> None:
        super().__init__(directory)
        self.set_sensor(0)

    @property
    def data(self) -> List[pd.DataFrame]:
        return self._data

    def _load_data_file(self, fp: str) -> DataFrame:
        df = super()._load_data_file(fp)

        elevation = np.deg2rad(df["elevation"])
        distance = df["distance"]
        azimuth_col_corrected = np.deg2rad(df["azimuth_col_corrected"])

        xy_distance = distance * np.cos(elevation)
        df["x"] = xy_distance * np.sin(azimuth_col_corrected)
        df["y"] = xy_distance * np.cos(azimuth_col_corrected)
        df["z"] = distance * np.sin(elevation)

        assert np.allclose(
            np.linalg.norm(df[["x", "y", "z"]], axis=1),
            df["distance"]
        )

        df.rename(columns={"intensity": "i"}, inplace=True)
        df["i"] = df["i"].astype(np.float64)
        df = df.assign(d=0)
        # df = df[["x", "y", "z", "i", "d"]]

        return df

class Camera(Sensor):
    @property
    def _data_file_extension(self) -> str:
        return 'jpg'

    @property
    def data(self) -> List[JpegImageFile]:
        """Returns Camera image array.

        Returns:
            List of camera images for each timestamp. Camera images are loaded as [``JpegImageFile``](https://pillow.readthedocs.io/en/stable/reference/plugins.html#PIL.JpegImagePlugin.JpegImageFile).
        """
        return self._data

    @property
    def poses(self) -> List[Dict[str, Dict[str, float]]]:
        """Returns Camera sensor pose array.

        Returns:
            A pose dictionary of the Camera sensor in world-coordinates for each frame. The dictionary keys return the following types:
             - `position`: `dict`
                - `x`: `float`
                    - Position of LiDAR sensor in world-coordinate system (x-axis) in meter
                - `y`: `float`
                    - Position of LiDAR sensor in world-coordinate system (y-axis) in meter
                - `z`: `float`
                    - Position of LiDAR sensor in world-coordinate system (z-axis) in meter
            - `heading`: `dict`
                - `w`: `float`
                    - Real part of _Quaternion_
                - `x`: `float`
                    - First imaginary part of _Quaternion_
                - `y`: `float`
                    - Second imaginary part of _Quaternion_
                - `z`: `float`
                    - Third imaginary part of _Quaternion_
        """
        return self._poses

    @property
    def timestamps(self) -> List[float]:
        """Returns Camera sensor recording timestamps array.

        Returns:
            A list of timestamps in `float` format for each camera image recorded in this sequence. To get point-wise timestamps, please refer to column `t` in `data` property return values.
        """
        return self._timestamps

    @property
    def intrinsics(self) -> 'Intrinsics':
        """Camera specific intrinsic data.

        Returns:
            Instance of class ``Intrinsics``
        """
        return self._intrinsics

    def __init__(self, directory: str) -> None:
        self._intrinsics_structure: str = None
        self._intrinsics: Intrinsics = None
        Sensor.__init__(self, directory)

    @overload
    def __getitem__(self, item: int) -> JpegImageFile:
        ...

    @overload
    def __getitem__(self, item: slice) -> List[JpegImageFile]:
        ...

    def __getitem__(self, item):
        return super().__getitem__(item)

    def load(self) -> None:
        super().load()
        self._load_intrinsics()

    def _load_structure(self) -> None:
        super()._load_structure()
        self._load_intrinsics_structure()

    def _load_intrinsics_structure(self) -> None:
        intrinsics_file = f'{self._directory}/intrinsics.json'
        if os.path.isfile(intrinsics_file):
            self._intrinsics_structure = intrinsics_file

    def _load_data_file(self, fp: str) -> JpegImageFile:
        # solve this bug: https://github.com/python-pillow/Pillow/issues/1237
        img = Image.open(fp)
        image = img.copy()
        img.close()
        return image
    
    def _load_intrinsics(self) -> None:
        with open(self._intrinsics_structure, 'r') as f:
            file_data = json.load(f)
            self._intrinsics = Intrinsics(fx=file_data['fx'],
                                          fy=file_data['fy'],
                                          cx=file_data['cx'],
                                          cy=file_data['cy'])


class Intrinsics:
    """Camera intrinsics

    Contains camera intrinsics with properties `fx`, `fy`, `cx`, `cy`, for easy usage with [OpenCV framework](https://docs.opencv.org/2.4/modules/calib3d/doc/camera_calibration_and_3d_reconstruction.html).
    There is no `skew` factor in the camera recordings.
    """

    @property
    def fx(self) -> float:
        """Focal length x-axis

        Returns:
            Focal length x-axis component
        """
        return self._fx

    @property
    def fy(self) -> float:
        """Focal length y-axis

        Returns:
            Focal length y-axis component
        """
        return self._fy

    @property
    def cx(self) -> float:
        """Principal point x-axis

        Returns:
            Principal point x-axis component
        """
        return self._cx

    @property
    def cy(self) -> float:
        """Principal point y-axis

        Returns:
            Principal point y-axis component
        """
        return self._cy

    def __init__(self, fx: float, fy: float, cx: float, cy: float):
        self._fx: float = fx
        self._fy: float = fy
        self._cx: float = cx
        self._cy: float = cy


if __name__ == '__main__':
    pass
