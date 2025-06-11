# Forced-Alignment-For-NicoKara

一个用于NicoKaraMaker的自动歌词时间轴对齐脚本，生成尽量接近直接使用的字幕文件。

---

## 更新

程序现在会使用 https://github.com/snakers4/silero-vad 尝试延长尾音

---

## 使用方法

[![在 Colab 中開啟](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/drive/1fxJaN8xhluWdJpXVh-ebo2r6hp8jxSYA)

或下载到设备上自行运行

---

## 输入要求

歌词文本需与音频内容一致，无论使用何种分离方式，均可能遇到分离后与歌词不匹配的情况（例如和声），请仔细确认。

### 1. 音频
- **格式**: `.mp3`
- **要求**: 使用从歌曲中的分离出的人声

### 2. 歌词
- **格式**: `.txt`

### 3. 自定义注音
程序自动注音可能出错。在歌词中可以使用双层括号 (()) 和斜杠 / 对特定日语自定义注音。
- **日语汉字**: 使用平假名，例如 ((未来/みらい))
- **特殊名词**: 使用罗马音，例如 ((イリジウム/irijiumu))

---

## 输出文件


- **`o.lrc`**: 主字幕
- **`o1.lrc`**: 导唱符
- **`o2.lrc`**: 罗马音（仅日语）字幕

---

## 效果演示

https://www.youtube.com/watch?v=YNfHwZTkfG0
