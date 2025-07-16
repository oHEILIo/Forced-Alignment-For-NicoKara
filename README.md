# 强制对齐歌词时间轴生成器

基于MMS_FA的自动歌词时间轴对齐工具，生成NicoKaraMaker兼容的字幕文件。

## 功能特性

- **智能文本分词**：精细化日语分词，支持自定义注音
- **音频强制对齐**：使用MMS_FA进行音频文本对齐
- **智能端点检测**：Silero VAD + 音量检测混合方法优化尾音
- **置信度微调**：基于对齐置信度的行级时间微调
- **多格式输出**：生成主字幕、导唱符、罗马音字幕

## 输入文件

- `i.txt` - 歌词文本文件
- `i.mp3` - 音频文件（建议使用人声分离后的音频）

### 自定义注音格式

使用双层括号和斜杠自定义注音：
- 日语汉字：`((未来/みらい))`
- 特殊名词：`((イリジウム/irijiumu))`

## 输出文件

- `o.lrc` - 主字幕文件
- `o1.lrc` - 导唱符文件  
- `o2.lrc` - 罗马音字幕文件

## 使用方法

```bash
python main.py
```

## 配置参数

在 `main.py` 中可调整以下参数：

```python
config = {
    'min_gap_seconds': 0.3,      # VAD最小间隔时间
    'volume_threshold': -40,      # 音量检测阈值(dB)
    'tolerance': 200,            # 端点合并容忍度(百分秒)
    'enable_vad_adjustment': True,    # 启用VAD端点调整
    'enable_score_correction': True,  # 启用置信度微调
    'debug_output': True         # 显示调试信息
}
```

## 项目结构

```
├── main.py        # 主程序入口
├── normalize.py   # 文本分词处理
├── align.py       # 音频对齐处理
├── formatter.py   # 输出格式化
├── utils.py       # 工具函数
├── i.txt          # 输入歌词
├── i.mp3          # 输入音频
├── o.lrc          # 输出主字幕
├── o1.lrc         # 输出导唱符
└── o2.lrc         # 输出罗马音
```

## 依赖库

```bash
pip install torch torchaudio librosa numpy janome pykakasi
```

## 算法优化

### 尾音处理优化
- 使用Silero VAD检测语音端点
- 结合音量检测进行验证
- 智能端点匹配算法

### 时间微调优化
- 按行分组处理，避免累积误差
- 基于置信度分数的相对调整
- 高分项目作为基准指导低分项目

## 注意事项

- 确保歌词与音频内容一致
- 建议使用高质量的人声分离音频
- 复杂歌词可能需要手动调整自定义注音