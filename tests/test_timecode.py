from core.timecode import seconds_to_timecode


def test_seconds_to_timecode() -> None:
    """验证 seconds_to_timecode 能将秒数正确格式化为 HH:MM:SS.mmm 时间码。"""
    assert seconds_to_timecode(0) == "00:00:00.000"
    assert seconds_to_timecode(65.4321) == "00:01:05.432"
    assert seconds_to_timecode(3661.2) == "01:01:01.200"
