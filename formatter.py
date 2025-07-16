from utils import parse_time_to_hundredths, format_hundredths_to_time_str

def process_main(result_list):
    """Generate main subtitle file content"""
    result = []
    current_line = ""
    last_end = None

    for item in result_list:
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
                    current_line = ""
                    last_end = None
            else:
                current_line += item['orig']

    if current_line and last_end:
        current_line += f"{last_end}"
        result.append(current_line)
    
    result.append("\n")
    return "".join(result)

def process_ruby(result_list):
    """Generate ruby annotation content"""
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

            # Find matching ruby4
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

def process_sign(result_list):
    """Generate sign markers for timing"""
    markers = []
    last_end_time = None
    line_started = False

    for i, item in enumerate(result_list):
        if ('start' in item and not line_started and item['type'] in [1, 2, 3]):
            current_start_time = parse_time_to_hundredths(item['start'])

            if ((last_end_time and current_start_time - last_end_time > 1000) or
                (last_end_time is None and current_start_time > 500)):
                marker_time = max(0, current_start_time - 300)
                marker_time_str = format_hundredths_to_time_str(marker_time)
                markers.append(f"{item['start']}⬤⬤⬤{marker_time_str}")
            
            line_started = True

        # Handle line end
        if item['type'] == 0 and item['orig'] == '\n':
            line_started = False
            for j in range(i - 1, -1, -1):
                if 'end' in result_list[j] and result_list[j]['type'] in [1, 2, 3]:
                    last_end_time = parse_time_to_hundredths(result_list[j]['end'])
                    break

    return "\n".join(markers) + "\n" if markers else ""

def process_pron(result_list):
    """Generate pronunciation subtitle file"""
    result = []
    current_line = ""
    last_end = None

    for item in result_list:
        if item['type'] in [2, 3]:
            if 'pron' in item and item['pron']:
                current_line += f"{item['start']}{item['pron']} "
                last_end = item['end']
        elif item['type'] == 0:
            if item['orig'] == '\n':
                if last_end:
                    current_line += f"{last_end}\n"
                    result.append(current_line)
                    current_line = ""
                    last_end = None

    if current_line and last_end:
        current_line += f"{last_end}"
        result.append(current_line)
    
    result.append("\n")
    return "".join(result)

def save_output_files(result_list):
    """Save all output files"""
    main_output = process_main(result_list)
    ruby_output = process_ruby(result_list)
    content = f"{main_output}\n{ruby_output}"
    sign_output = process_sign(result_list)
    pron_output = process_pron(result_list)
    
    with open('o.lrc', 'w', encoding='utf-8') as f:
        f.write(content)
    with open('o1.lrc', 'w', encoding='utf-8') as f:
        f.write(sign_output)
    with open('o2.lrc', 'w', encoding='utf-8') as f:
        f.write(pron_output)