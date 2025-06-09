import normalize
import align
import re

def parse_time_to_hundredths(time_str):
    match = re.match(r'\[(\d{2}):(\d{2}):(\d{2})\]', time_str)
    minutes, seconds, hundredths = int(match.group(1)), int(match.group(2)), int(match.group(3))
    return minutes * 6000 + seconds * 100 + hundredths

def format_hundredths_to_time_str(total_hundredths):
    minutes = total_hundredths // 6000
    remaining = total_hundredths % 6000
    seconds = remaining // 100
    hundredths = remaining % 100
    return f"[{minutes:02d}:{seconds:02d}:{hundredths:02d}]"

def process_main(result_list):
    result = []
    current_line = ""
    last_end = None
    last_end_time = None

    i = 0
    while i < len(result_list):
        item = result_list[i]

        if ('start' in item and current_line == "" and item['type'] in [1, 2, 3]):
            current_start_time = parse_time_to_hundredths(item['start'])

            if ((last_end_time and current_start_time - last_end_time > 1000) or
                (last_end_time is None and current_start_time > 500)):
                marker_time = max(0, current_start_time - 300)
                marker_time_str = format_hundredths_to_time_str(marker_time)
                current_line += f"{marker_time_str}⬤⬤⬤"

        if item['type'] in [1, 3]:
            current_line += f"{item['start']}{item['orig']}"
            last_end = item['end']
        elif item['type'] == 2:
            if item['orig'] != '':
                current_line += f"{item['start']}{item['orig']}"
            last_end = item['end']
        elif item['type'] == 0:
            if item['orig'] == '\n':
                if last_end:
                    current_line += f"{last_end}\n"
                    result.append(current_line)
                    last_end_time = parse_time_to_hundredths(last_end)
                    current_line = ""
                    last_end = None
            else:
                current_line += item['orig']
        i += 1

    if current_line and last_end:
        current_line += f"{last_end}"
        result.append(current_line)
    result.append("\n")
    return "".join(result)

def process_ruby(result_list):
    ruby_annotations = []
    i = 0

    while i < len(result_list):
        item = result_list[i]

        if item['type'] == 2 and item['orig'] != '':
            ruby1 = item['orig']
            ruby2 = item['ruby']
            ruby3 = item['start']
            ruby4 = ''

            first_start_time = parse_time_to_hundredths(item['start'])

            j = i + 1
            while j < len(result_list) and result_list[j]['type'] == 2 and result_list[j]['orig'] == '':
                current_item = result_list[j]
                current_start_time = parse_time_to_hundredths(current_item['start'])
                time_diff = current_start_time - first_start_time
                time_diff_str = format_hundredths_to_time_str(time_diff)
                ruby2 += f"{time_diff_str}{current_item['ruby']}"
                j += 1

            for k in range(len(ruby_annotations) - 1, -1, -1):
                if ruby_annotations[k]['ruby1'] == ruby1:
                    ruby_annotations[k]['ruby4'] = item['start']
                    break

            ruby_annotations.append({'ruby1': ruby1, 'ruby2': ruby2, 'ruby3': ruby3, 'ruby4': ruby4})
            i = j
        else:
            i += 1

    result = []
    for idx, annotation in enumerate(ruby_annotations, 1):
        result.append(f"@Ruby{idx}={annotation['ruby1']},{annotation['ruby2']},{annotation['ruby3']},{annotation['ruby4']}")

    return "\n".join(result)

def process_pron(result_list):
    result = []
    current_line = ""
    last_end = None
    last_end_time = None

    i = 0
    while i < len(result_list):
        item = result_list[i]

        # 处理不同类型的项目
        if item['type'] in [2, 3]:
            # 对于 type 2, 3，使用 pron 并添加空格
            if 'pron' in item and item['pron']:
                current_line += f"{item['start']}{item['pron']} "
                last_end = item['end']
        elif item['type'] == 0:
            # 对于 type 0，只处理换行符
            if item['orig'] == '\n':
                if last_end:
                    current_line += f"{last_end}\n"
                    result.append(current_line)
                    last_end_time = parse_time_to_hundredths(last_end)
                    current_line = ""
                    last_end = None
            # 其他 type 0 项目（如空格、标点符号）跳过
        # type 1 项目完全跳过

        i += 1

    # 处理最后一行
    if current_line and last_end:
        current_line += f"{last_end}"
        result.append(current_line)
    result.append("\n")
    return "".join(result)

def main():
    result_list = []
    with open('i.txt', 'r', encoding='utf-8') as file:
        for line in file:
            if line.strip():
                #print(f"process line:{line.strip()}")
                result_list.extend(normalize.process_line(line))
                result_list.append({'orig': '\n', 'type': 0})
                #print("")

    alignment_tokens = []
    token_to_index_map = {}
    for i, item in enumerate(result_list):
        if 'pron' in item and item['pron']:
            alignment_tokens.append(item['pron'])
            token_to_index_map[len(alignment_tokens) - 1] = i

    for item in alignment_tokens:
        if normalize.is_english(item):
            continue
        else:
            print(f"alignment_tokens可能包含错误数据{item}")

    alignment_results = align.align_audio_with_text('i.mp3', alignment_tokens)
    for i, result in enumerate(alignment_results):
        if i in token_to_index_map:
            original_index = token_to_index_map[i]
            result_list[original_index]['start'] = result['start']
            result_list[original_index]['end'] = result['end']

    for item in result_list:
        print(item)

    main_output = process_main(result_list)
    ruby_output = process_ruby(result_list)
    content = f"{main_output}\n{ruby_output}"
    pron_output = process_pron(result_list)
    with open('o.lrc', 'w', encoding='utf-8') as f:
        f.write(content)
    with open('o2.lrc', 'w', encoding='utf-8') as f:
        f.write(pron_output)

if __name__ == "__main__":
    main()