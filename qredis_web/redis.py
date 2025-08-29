import pickle
import collections
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

import msgpack
import msgpack_numpy
from redis import Redis

from qredis.util import KeyItem


# Encoding helpers (duplicated from qredis.redis to avoid Qt dependency)

def msgpack_pack(data: Any) -> bytes:
    return msgpack.packb(data, use_bin_type=True, default=msgpack_numpy.encode)


def msgpack_unpack(buff: bytes) -> Any:
    return msgpack.unpackb(buff, raw=False, object_hook=msgpack_numpy.decode)


def decode_utf8(v: bytes) -> str:
    return v.decode()


def decode_pickle(v: bytes) -> str:
    return str(pickle.loads(v))


def decode_msgpack(v: bytes) -> str:
    return str(msgpack_unpack(v))


DECODES = [
    (decode_utf8, "utf-8"),
    (decode_pickle, "pickle"),
    (decode_msgpack, "msgpack"),
    (str, "raw"),
]


def decode(value: Optional[bytes]) -> Optional[str]:
    if value is None:
        return None
    for decoder, _dtype in DECODES:
        try:
            return decoder(value)  # type: ignore[arg-type]
        except Exception:
            continue
    return None


class zset(list):
    pass


class stream(tuple):
    pass


class WebRedis:
    """A Qt-free wrapper around redis.Redis with typed getters.

    Returns qredis.util.KeyItem for get(), mirroring QRedis.get but without Qt signals.
    """

    TYPE_MAP = {
        type(None): "none",
        str: "string",
        dict: "hash",
        list: "list",
        set: "set",
        zset: "zset",
        stream: "stream",
    }

    def __init__(self, *args, **kwargs) -> None:
        self.redis = Redis(*args, **kwargs)
        self._get_type_map = {
            "none": lambda k: None,
            "string": self._get,
            "hash": self._hgetall,
            "list": self._lgetall,
            "set": self._sgetall,
            "zset": self._zgetall,
            "stream": self._xrange,
        }

    # Typed getters
    def _get(self, key: str) -> Optional[str]:
        return decode(self.redis.get(key))

    def _hgetall(self, key: str) -> Dict[str, str]:
        return {decode(k) or "": decode(v) or "" for k, v in self.redis.hgetall(key).items()}

    def _lgetall(self, key: str) -> List[str]:
        return [decode(i) or "" for i in self.redis.lrange(key, 0, -1)]

    def _sgetall(self, key: str) -> Set[str]:
        return {decode(i) or "" for i in self.redis.smembers(key)}

    def _zgetall(self, key: str) -> Dict[str, str]:
        return {decode(member) or "": decode(score) or "" for member, score in self.redis.zscan_iter(key)}

    def _xrange(self, key: str) -> List[Tuple[str, Dict[str, str]]]:
        data: List[Tuple[str, Dict[str, str]]] = []
        for entry_id, entry_data_raw in self.redis.xrange(key):
            event_time = decode(entry_id) or ""
            event_data = {decode(member) or "": decode(score) or "" for member, score in entry_data_raw.items()}
            data.append((event_time, event_data))
        return data

    # Public API
    def type(self, name: str) -> str:
        return self.redis.type(name).decode()

    def ttl(self, key: str) -> int:
        ttl = self.redis.ttl(key)
        return -1 if ttl is None else int(ttl)

    def exists(self, key: str) -> bool:
        return bool(self.redis.exists(key))

    def has_key(self, key: str) -> bool:
        return self.exists(key)

    def get(self, key: str, default: Optional[Any] = None) -> KeyItem:
        if not self.exists(key):
            return default  # type: ignore[return-value]
        dtype = self.type(key)
        ttl = self.ttl(key)
        value = self._get_type_map[dtype](key)
        return KeyItem(self, key, dtype, ttl, value)

    def scan(self, cursor: int = 0, match: str = "*", count: int = 100) -> Tuple[int, List[str]]:
        next_cursor, keys = self.redis.scan(cursor=cursor, match=match, count=count)
        return int(next_cursor), [k.decode() if isinstance(k, (bytes, bytearray)) else str(k) for k in keys]

    def keys(self, pattern: str = "*") -> List[str]:
        return [k.decode() for k in self.redis.keys(pattern)]

    def delete(self, *keys: str) -> int:
        return int(self.redis.delete(*keys))

    def rename(self, old_key: str, new_key: str) -> None:
        self.redis.rename(old_key, new_key)

    # Simple setter (currently string-only for MVP)
    def set_string(self, key: str, value: str, ttl: Optional[int] = None) -> None:
        self.redis.set(key, value)
        if ttl is not None and ttl >= 0:
            self.redis.expire(key, ttl)

    def info(self) -> Dict[str, Any]:
        return self.redis.info()  # type: ignore[no-any-return]

