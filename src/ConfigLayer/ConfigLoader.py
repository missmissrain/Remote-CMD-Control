# -*- coding: utf-8 -*-
"""配置加载层

功能：读取并校验项目 config 目录下的 JSON 配置。
实现：将 JSON 文件解析为字典，提供按点号路径取值的便捷方法。
注册参数：
    configPath -- 配置文件的绝对路径或相对项目根目录的路径（默认 "config/ServerConfig.json"）
    rootDir    -- 项目根目录（默认取本文件向上两级目录）
默认参数说明：
    相对路径会以 rootDir 为基准解析，便于在任意工作目录下运行脚本。
"""

import json
import os


class ConfigLoader:
    """JSON 配置读取器。"""

    def __init__(self, config_path="config/ServerConfig.json", root_dir=None):
        # 项目根目录：本文件位于 <root>/src/ConfigLayer/ 下，向上两级即为根目录
        self._root_dir = root_dir or os.path.abspath(
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
        )
        self._config_path = (
            config_path
            if os.path.isabs(config_path)
            else os.path.join(self._root_dir, config_path)
        )
        self._data = self._load_json()

    def _load_json(self):
        """无参数。读取配置文件并返回解析后的字典，文件缺失时抛出异常。"""
        if not os.path.isfile(self._config_path):
            raise FileNotFoundError("配置文件不存在: %s" % self._config_path)
        with open(self._config_path, "r", encoding="utf-8") as handle:
            return json.load(handle)

    def get(self, key_path, default=None):
        """key_path：以点号分隔的键路径，如 "server.host"。
        返回对应值；路径不存在时返回 default。"""
        node = self._data
        for key in key_path.split("."):
            if not isinstance(node, dict) or key not in node:
                return default
            node = node[key]
        return node

    def require(self, key_path):
        """key_path：以点号分隔的键路径。返回值，但缺失时直接抛出异常。"""
        value = self.get(key_path)
        if value in (None, ""):
            raise KeyError("配置项缺失: %s" % key_path)
        return value

    @property
    def root_dir(self):
        """无参数。返回项目根目录。"""
        return self._root_dir
