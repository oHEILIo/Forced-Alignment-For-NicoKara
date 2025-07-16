import re
import math

def parse_time_to_hundredths(time_str):
    """Convert time string [MM:SS:CC] to hundredths of seconds"""
    match = re.match(r'\[(\d{2}):(\d{2}):(\d{2})\]', time_str)
    if not match:
        return 0
    minutes, seconds, hundredths = int(match.group(1)), int(match.group(2)), int(match.group(3))
    return minutes * 6000 + seconds * 100 + hundredths

def format_hundredths_to_time_str(total_hundredths):
    """Convert hundredths of seconds to time string [MM:SS:CC]"""
    minutes = total_hundredths // 6000
    remaining = total_hundredths % 6000
    seconds = remaining // 100
    hundredths = remaining % 100
    return f"[{minutes:02d}:{seconds:02d}:{hundredths:02d}]"

def format_time_from_seconds(time_sec):
    """Convert seconds to time string [MM:SS:CC]"""
    minutes, remainder = divmod(time_sec, 60)
    seconds, centiseconds = divmod(remainder, 1)
    return f"[{int(minutes):02d}:{int(seconds):02d}:{math.floor(centiseconds * 100):02d}]"

def is_english(text):
    """Check if text contains only English characters"""
    return bool(re.match(r'^[a-zA-Z]+$', text))

def is_kanji(char):
    """Check if character is kanji"""
    return ('\u4E00' <= char <= '\u9FFF' or '\u3400' <= char <= '\u4DBF' or
            '\uF900' <= char <= '\uFAFF' or char == '\u3005')

def is_hiragana(char):
    """Check if character is hiragana"""
    return '\u3040' <= char <= '\u309F'

def is_katakana(char):
    """Check if character is katakana"""
    return '\u30A0' <= char <= '\u30FF'

def is_kana(char):
    """Check if character is kana (excluding special symbols)"""
    if char in ['・', '゠', 'ー']:
        return False
    return is_hiragana(char) or is_katakana(char)