from __future__ import annotations


def seconds_to_timecode(seconds: float) -> str:
    """将秒数转换为 HH:MM:SS.mmm 时间码格式。"""
    total_ms = int(round(seconds * 1000))
    ms = total_ms % 1000
    total_seconds = total_ms // 1000
    sec = total_seconds % 60
    total_minutes = total_seconds // 60
    minute = total_minutes % 60
    hour = total_minutes // 60
    return f"{hour:02d}:{minute:02d}:{sec:02d}.{ms:03d}"
