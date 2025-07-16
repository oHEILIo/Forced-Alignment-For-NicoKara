import normalize
import align
import formatter
import re
from utils import is_english

def main():
    """Main entry point with parameter adjustment capabilities"""
    # Configuration parameters - easily adjustable
    config = {
        'input_text': 'i.txt',
        'input_audio': 'i.mp3',
        'min_gap_seconds': 0.3,
        'volume_threshold': -40,
        'tolerance': 200,
        'enable_vad_adjustment': True,
        'enable_score_correction': True,
        'debug_output': True
    }
    
    print("开始处理文本...")
    result_list = process_input_text(config['input_text'])
    
    print("开始音频对齐...")
    alignment_tokens, token_to_index_map = prepare_alignment_tokens(result_list)
    
    # Validate alignment tokens
    validate_alignment_tokens(alignment_tokens)
    
    # Perform alignment
    alignment_results = align.align_audio_with_text(config['input_audio'], alignment_tokens)
    
    # Apply alignment results to result_list
    apply_alignment_results(result_list, alignment_results, token_to_index_map)
    
    # Apply VAD adjustment if enabled
    if config['enable_vad_adjustment']:
        print("开始使用混合方法（Silero VAD + 音量检测）调整end时间...")
        align.adjust_ends_with_hybrid(
            result_list, 
            config['input_audio'], 
            min_gap_seconds=config['min_gap_seconds'],
            volume_threshold=config['volume_threshold'], 
            tolerance=config['tolerance']
        )
        print("混合方法调整完成")
    
    # Apply score-based correction if enabled
    if config['enable_score_correction']:
        print("开始基于置信度分数的微调...")
        apply_score_based_correction(result_list)
        print("分数微调完成")
    
    # Debug output
    if config['debug_output']:
        print("\n处理结果:")
        for item in result_list:
            print(item)
    
    # Generate output files
    print("生成输出文件...")
    formatter.save_output_files(result_list)
    print("处理完成！")

def process_input_text(input_file):
    """Process input text file and return token list"""
    result_list = []
    with open(input_file, 'r', encoding='utf-8') as file:
        for line in file:
            if line.strip():
                # Split custom pronunciation patterns
                parts = re.split(r'(\(\([^)]*\)\))', line.strip())  
                for part in parts:
                    if part:
                        if part.startswith('((') and part.endswith('))'):
                            content = part[2:-2]
                            result_list.extend(normalize.process_custon(content))
                        else:
                            result_list.extend(normalize.process_token(part))
                result_list.append({'orig': '\n', 'type': 0})
    return result_list

def prepare_alignment_tokens(result_list):
    """Prepare tokens for alignment and create mapping"""
    alignment_tokens = []
    token_to_index_map = {}
    
    for i, item in enumerate(result_list):
        if 'pron' in item and item['pron']:
            alignment_tokens.append(item['pron'])
            token_to_index_map[len(alignment_tokens) - 1] = i
    
    return alignment_tokens, token_to_index_map

def validate_alignment_tokens(alignment_tokens):
    """Validate alignment tokens for potential issues"""
    for item in alignment_tokens:
        if not is_english(item):
            print(f"警告: alignment_tokens可能包含错误数据: {item}")

def apply_alignment_results(result_list, alignment_results, token_to_index_map):
    """Apply alignment results to the result list"""
    for i, result in enumerate(alignment_results):
        if i in token_to_index_map:
            original_index = token_to_index_map[i]
            result_list[original_index]['start'] = result['start']
            result_list[original_index]['end'] = result['end']
            result_list[original_index]['score'] = result['score']

def apply_score_based_correction(result_list):
    """
    基于置信度分数的智能行级微调算法
    以每行为单位，用高分项目作为基准调整低分项目
    """
    print("开始基于置信度的行级时间微调...")
    
    # 按行分组处理
    lines = group_items_by_line(result_list)
    
    total_adjustments = 0
    for line_items in lines:
        adjustments = process_line_score_adjustment(line_items)
        total_adjustments += adjustments
    
    if total_adjustments > 0:
        print(f"完成行级微调，共调整了 {total_adjustments} 个时间点")
    else:
        print("未发现需要调整的时间点")

def group_items_by_line(result_list):
    """将result_list按行分组，每两个换行符之间为一行"""
    lines = []
    current_line = []
    
    for item in result_list:
        if item['type'] == 0 and item['orig'] == '\n':
            if current_line:
                lines.append(current_line)
                current_line = []
        else:
            current_line.append(item)
    
    # 处理最后一行（如果没有以换行符结尾）
    if current_line:
        lines.append(current_line)
    
    return lines

def process_line_score_adjustment(line_items):
    """
    处理单行的分数调整
    返回调整的项目数量
    """
    # 筛选有时间信息和分数的项目
    timed_items = [item for item in line_items 
                   if 'start' in item and 'end' in item and 'score' in item]
    
    if len(timed_items) < 4:  # 条目数太少则跳过
        return 0
    
    # 按分数排序
    sorted_items = sorted(timed_items, key=lambda x: x['score'], reverse=True)
    
    # 分为高分组和低分组
    mid_point = len(sorted_items) // 2
    high_score_items = sorted_items[:mid_point]
    low_score_items = sorted_items[mid_point:]
    
    # 检查高分组的质量
    high_score_avg = sum(item['score'] for item in high_score_items) / len(high_score_items)
    if high_score_avg < 0.5:
        print(f"警告: 检测到整体得分较低的行 (平均分: {high_score_avg:.3f})，可能影响调整效果")
        return 0
    
    # 执行调整
    return adjust_low_score_items(high_score_items, low_score_items)

def adjust_low_score_items(high_score_items, low_score_items):
    """
    基于高分项目调整低分项目的时间
    """
    from utils import parse_time_to_hundredths, format_hundredths_to_time_str
    
    # 构建高分项目的时间基准
    high_score_times = []
    for item in high_score_items:
        start_time = parse_time_to_hundredths(item['start'])
        end_time = parse_time_to_hundredths(item['end'])
        high_score_times.append((start_time, end_time, item['score']))
    
    # 按时间排序
    high_score_times.sort(key=lambda x: x[0])
    
    adjustments_made = 0
    
    for low_item in low_score_items:
        current_start = parse_time_to_hundredths(low_item['start'])
        current_end = parse_time_to_hundredths(low_item['end'])
        
        # 找到最佳的调整参考
        adjustment = calculate_optimal_adjustment(
            current_start, current_end, high_score_times, low_item['score']
        )
        
        if adjustment != 0:
            # 应用调整
            new_start = max(0, current_start + adjustment)
            new_end = max(new_start + 10, current_end + adjustment)  # 确保end > start
            
            # 验证调整的合理性
            if is_adjustment_valid(new_start, new_end, high_score_times):
                low_item['start'] = format_hundredths_to_time_str(new_start)
                low_item['end'] = format_hundredths_to_time_str(new_end)
                adjustments_made += 1
    
    return adjustments_made

def calculate_optimal_adjustment(current_start, current_end, high_score_times, current_score):
    """
    计算最优的时间调整量
    """
    if not high_score_times:
        return 0
    
    # 找到时间上最接近的高分项目
    closest_ref = min(high_score_times, 
                     key=lambda x: abs(x[0] - current_start))
    
    ref_start, ref_end, ref_score = closest_ref
    
    # 计算调整强度（基于分数差异）
    score_diff = ref_score - current_score
    if score_diff <= 0:
        return 0
    
    # 计算时间差异
    time_diff = current_start - ref_start
    
    # 调整策略：分数差异越大，调整越明显，但有上限
    max_adjustment = min(50, abs(time_diff) * 0.3)  # 最大调整0.5秒
    adjustment_ratio = min(score_diff * 2, 1.0)  # 调整比例
    
    adjustment = int(max_adjustment * adjustment_ratio)
    
    # 如果当前时间明显早于参考时间，适当延后
    if time_diff < -100:  # 早于参考时间1秒以上
        return adjustment
    elif time_diff > 100:  # 晚于参考时间1秒以上
        return -adjustment
    
    return 0

def is_adjustment_valid(new_start, new_end, high_score_times):
    """
    验证调整后的时间是否合理
    """
    # 基本合理性检查
    if new_start >= new_end:
        return False
    
    # 检查是否与高分项目时间冲突
    for ref_start, ref_end, _ in high_score_times:
        # 避免严重重叠
        if (new_start < ref_end and new_end > ref_start):
            overlap = min(new_end, ref_end) - max(new_start, ref_start)
            if overlap > (new_end - new_start) * 0.5:  # 重叠超过50%
                return False
    
    return True

if __name__ == "__main__":
    main()
