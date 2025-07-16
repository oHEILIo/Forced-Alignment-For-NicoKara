import torch
import torchaudio
import librosa
import numpy as np
from utils import parse_time_to_hundredths, format_hundredths_to_time_str, format_time_from_seconds

def align_audio_with_text(audio_file_path, text_tokens):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    try:
        bundle = torchaudio.pipelines.MMS_FA
        waveform, sample_rate = torchaudio.load(audio_file_path)
        waveform = waveform.mean(0, keepdim=True)
        waveform = torchaudio.functional.resample(
            waveform, sample_rate, int(bundle.sample_rate)
        )
        model = bundle.get_model().to(device)
        tokenizer = bundle.get_tokenizer()
        aligner = bundle.get_aligner()
        valid_tokens = [token for token in text_tokens if token]
        with torch.inference_mode():
            emission, _ = model(waveform.to(device))
            tokens = tokenizer(valid_tokens)
            token_spans = aligner(emission[0], tokens)
        results = []
        frame_duration = 1.0 / bundle.sample_rate * 320
        for i, spans in enumerate(token_spans):
            if not spans:
                results.append({
                    'token': valid_tokens[i],
                    'start': '[error]',
                    'end': '[error]',
                    'score': 0.0  # 添加score，错误时设为0
                })
                continue
            start_time = spans[0].start * frame_duration
            end_time = spans[-1].end * frame_duration
            
            # 计算置信度分数 - 可以取平均值
            confidence_scores = [span.score for span in spans]
            avg_score = sum(confidence_scores) / len(confidence_scores)
            
            results.append({
                'token': valid_tokens[i],
                'start': format_time_from_seconds(start_time),
                'end': format_time_from_seconds(end_time),
                'score': round(avg_score, 4)  # 添加score，保留4位小数
            })
        return results
    except Exception as e:
        print(f"Error during alignment: {e}")
        return []

def get_silero_endpoints(audio_file, min_gap_seconds=0.3):
    """获取Silero VAD的端点时间（百分秒格式）"""
    model, utils = torch.hub.load(repo_or_dir='snakers4/silero-vad',
                                  model='silero_vad',
                                  force_reload=False,
                                  trust_repo=True)
    
    get_speech_timestamps = utils[0]
    read_audio = utils[2]
    
    wav = read_audio(audio_file)
    speech_timestamps = get_speech_timestamps(
        wav, 
        model,
        min_silence_duration_ms=int(min_gap_seconds * 1000)
    )
    
    # 转换为百分秒格式
    endpoints = []
    for timestamp in speech_timestamps:
        end_time_seconds = timestamp['end'] / 16000
        hundredths = int(end_time_seconds * 100)
        endpoints.append(hundredths)
    
    return endpoints

def get_volume_endpoints(audio_file, min_gap_seconds=0.3, volume_threshold=-40):
    """使用音量检测获取端点时间（百分秒格式）"""
    # 加载音频
    y, sr = librosa.load(audio_file, sr=None)
    
    # 计算RMS能量（音量）
    frame_length = int(0.025 * sr)  # 25ms窗口
    hop_length = int(0.01 * sr)     # 10ms步长
    
    rms = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)[0]
    
    # 转换为dB
    rms_db = librosa.amplitude_to_db(rms, ref=np.max)
    
    # 检测语音段
    is_speech = rms_db > volume_threshold
    
    # 找到语音段的开始和结束
    speech_segments = []
    in_speech = False
    start_frame = 0
    
    for i, speech in enumerate(is_speech):
        if speech and not in_speech:
            start_frame = i
            in_speech = True
        elif not speech and in_speech:
            # 语音段结束
            start_time = start_frame * hop_length / sr
            end_time = i * hop_length / sr
            
            # 检查段落长度，过滤太短的段落
            if end_time - start_time > 0.1:  # 至少100ms
                speech_segments.append((start_time, end_time))
            in_speech = False
    
    # 处理最后一个段落
    if in_speech:
        start_time = start_frame * hop_length / sr
        end_time = len(is_speech) * hop_length / sr
        if end_time - start_time > 0.1:
            speech_segments.append((start_time, end_time))
    
    # 合并间隔小于min_gap_seconds的段落
    merged_segments = []
    for start, end in speech_segments:
        if merged_segments and start - merged_segments[-1][1] < min_gap_seconds:
            # 合并到前一个段落
            merged_segments[-1] = (merged_segments[-1][0], end)
        else:
            merged_segments.append((start, end))
    
    # 提取端点（只返回结束时间）
    endpoints = []
    for _, end_time in merged_segments:
        hundredths = int(end_time * 100)
        endpoints.append(hundredths)
    
    return endpoints

def merge_endpoints(silero_endpoints, volume_endpoints, tolerance=200):
    """
    合并两种方法的端点，优先选择更准确的端点
    
    参数:
    - silero_endpoints: Silero VAD的端点列表
    - volume_endpoints: 音量检测的端点列表
    - tolerance: 容忍度（百分秒），在此范围内的端点被认为是同一个
    
    返回:
    - merged_endpoints: 合并后的端点列表，每个端点包含来源信息
    """
    merged_endpoints = []
    
    # 将两种端点标记来源并合并
    all_endpoints = []
    for ep in silero_endpoints:
        all_endpoints.append({'time': ep, 'source': 'silero'})
    for ep in volume_endpoints:
        all_endpoints.append({'time': ep, 'source': 'volume'})
    
    # 按时间排序
    all_endpoints.sort(key=lambda x: x['time'])
    
    i = 0
    while i < len(all_endpoints):
        current = all_endpoints[i]
        candidates = [current]
        
        # 收集在容忍范围内的所有端点
        j = i + 1
        while j < len(all_endpoints) and all_endpoints[j]['time'] - current['time'] <= tolerance:
            candidates.append(all_endpoints[j])
            j += 1
        
        # 选择最佳端点
        best_endpoint = choose_best_endpoint(candidates)
        merged_endpoints.append(best_endpoint)
        
        i = j
    
    return merged_endpoints

def choose_best_endpoint(candidates):
    """
    从候选端点中选择最佳的端点
    
    优先级规则:
    1. 如果只有一种来源，直接使用
    2. 如果两种来源都有，优先使用Silero（语音特征更准确）
    3. 如果有多个同类型端点，选择时间居中的
    """
    if len(candidates) == 1:
        return candidates[0]
    
    # 分组
    silero_candidates = [c for c in candidates if c['source'] == 'silero']
    volume_candidates = [c for c in candidates if c['source'] == 'volume']
    
    # 如果两种来源都有，优先选择Silero
    if silero_candidates and volume_candidates:
        # 选择Silero中时间最接近volume平均值的
        volume_avg = sum(c['time'] for c in volume_candidates) / len(volume_candidates)
        best_silero = min(silero_candidates, key=lambda x: abs(x['time'] - volume_avg))
        best_silero['confidence'] = 'high'  # 两种方法都检测到，置信度高
        return best_silero
    
    # 只有一种来源
    if silero_candidates:
        best = silero_candidates[len(silero_candidates)//2]  # 选择中位数
        best['confidence'] = 'medium'
        return best
    else:
        best = volume_candidates[len(volume_candidates)//2]  # 选择中位数
        best['confidence'] = 'medium'
        return best

def adjust_ends_with_hybrid(result_list, audio_file, min_gap_seconds=0.3, volume_threshold=-40, tolerance=200):
    """
    使用混合方法（Silero VAD + 音量检测）调整result_list中的end时间
    优化了端点匹配逻辑，提高了尾音处理的准确性
    """
    try:
        print("开始获取Silero VAD端点...")
        silero_endpoints = get_silero_endpoints(audio_file, min_gap_seconds)
        print(f"Silero VAD检测到 {len(silero_endpoints)} 个端点")
        
        print("开始获取音量检测端点...")
        volume_endpoints = get_volume_endpoints(audio_file, min_gap_seconds, volume_threshold)
        print(f"音量检测到 {len(volume_endpoints)} 个端点")
        
        if not silero_endpoints and not volume_endpoints:
            print("两种方法都未检测到端点，不进行调整")
            return
        
        # 合并端点
        merged_endpoints = merge_endpoints(silero_endpoints, volume_endpoints, tolerance)
        print(f"合并后共 {len(merged_endpoints)} 个端点")
        
        # 应用智能端点匹配
        apply_smart_endpoint_matching(result_list, merged_endpoints)
        
    except Exception as e:
        print(f"端点调整过程中出现错误: {e}")
        print("跳过端点调整，继续处理...")

def apply_smart_endpoint_matching(result_list, merged_endpoints):
    """
    智能端点匹配算法，改进了原有的简单匹配逻辑
    """
    # 收集所有有end的项目
    end_items = [(i, parse_time_to_hundredths(item['end'])) 
                 for i, item in enumerate(result_list) if 'end' in item]
    
    if not end_items:
        print("result_list中没有end项目")
        return
    
    print(f"开始匹配 {len(end_items)} 个end项目与 {len(merged_endpoints)} 个端点")
    
    # 为每个end项目找到最佳匹配的端点
    for i, (item_index, current_end) in enumerate(end_items):
        best_endpoint = find_best_endpoint_match(
            current_end, merged_endpoints, end_items, i
        )
        
        if best_endpoint:
            new_end_time = best_endpoint['time']
            # 只有当新端点明显更好时才调整
            if should_adjust_endpoint(current_end, new_end_time, best_endpoint):
                result_list[item_index]['end'] = format_hundredths_to_time_str(new_end_time)
                print(f"调整end: {format_hundredths_to_time_str(current_end)} -> "
                      f"{format_hundredths_to_time_str(new_end_time)} "
                      f"(来源: {best_endpoint['source']}, 置信度: {best_endpoint.get('confidence', 'medium')})")

def find_best_endpoint_match(current_end, merged_endpoints, end_items, current_index):
    """
    为当前end时间找到最佳匹配的端点
    """
    # 定义搜索范围
    search_range = 500  # 5秒范围内搜索
    
    # 获取相邻end项目的时间约束
    prev_end = end_items[current_index - 1][1] if current_index > 0 else 0
    next_end = end_items[current_index + 1][1] if current_index < len(end_items) - 1 else float('inf')
    
    # 在合理范围内寻找候选端点
    candidates = []
    for endpoint in merged_endpoints:
        ep_time = endpoint['time']
        
        # 端点必须在当前时间附近，且不能超出相邻项目的范围
        if (abs(ep_time - current_end) <= search_range and 
            prev_end < ep_time < next_end):
            
            # 计算匹配分数
            distance_score = 1.0 - (abs(ep_time - current_end) / search_range)
            confidence_score = 1.0 if endpoint.get('confidence') == 'high' else 0.7
            source_score = 1.0 if endpoint['source'] == 'silero' else 0.8
            
            total_score = distance_score * confidence_score * source_score
            candidates.append((endpoint, total_score))
    
    # 返回得分最高的候选
    if candidates:
        return max(candidates, key=lambda x: x[1])[0]
    return None

def should_adjust_endpoint(current_end, new_end, endpoint_info):
    """
    判断是否应该调整端点
    """
    time_diff = abs(new_end - current_end)
    
    # 如果时间差很小，不调整
    if time_diff < 20:  # 0.2秒
        return False
    
    # 如果是高置信度的端点，且时间差合理，则调整
    if endpoint_info.get('confidence') == 'high' and time_diff < 300:  # 3秒
        return True
    
    # 如果新端点明显更晚（处理尾音延长），且来源可靠
    if (new_end > current_end and 
        time_diff < 200 and  # 2秒内
        endpoint_info['source'] == 'silero'):
        return True
    
    return False