from janome.tokenizer import Tokenizer
import pykakasi
import re
from utils import is_english, is_kanji, is_hiragana, is_katakana, is_kana

# Initialize tokenizers once for better performance
kks = pykakasi.kakasi()
tokenizer = Tokenizer()

def match_token(surface, phonetic):
    result = []
    s_idx = p_idx = last_match_s = last_match_p = 0

    while s_idx < len(surface):
        char = surface[s_idx]
        if is_kana(char):
            matched = False
            for j in range(len(phonetic) - p_idx):
                if (phonetic[p_idx + j] == char and
                    (p_idx + j + 1 >= len(phonetic) or phonetic[p_idx + j + 1] != char)):

                    inter_surface = surface[last_match_s:s_idx]
                    inter_phonetic = phonetic[last_match_p:p_idx+j]
                    if inter_surface and inter_phonetic:
                        result.append((inter_surface, inter_phonetic))

                    result.append((char, char))
                    last_match_s = s_idx + 1
                    last_match_p = p_idx + j + 1
                    s_idx += 1
                    p_idx = p_idx + j + 1
                    matched = True
                    break
            if not matched:
                s_idx += 1
        else:
            s_idx += 1

    remaining_surface = surface[last_match_s:]
    remaining_phonetic = phonetic[last_match_p:]
    if remaining_surface and remaining_phonetic:
        result.append((remaining_surface, remaining_phonetic))

    return result

def process_custon(content):
    token_list = []
    if '/' in content:
        parts = content.split('/', 1)
        orig = parts[0]
        ruby = parts[1]
        if any(is_kanji(c) for c in orig):
            for ri in ruby:
                pi = kks.convert(ri)[0]['hepburn']
                token_list.append({'orig': orig, 'type': 2, 'pron': pi, 'ruby': ri})
                orig = ''
        else:
            token_list.append({'orig': orig, 'type': 3, 'pron': ruby})
    return token_list

def process_token(line):
    token_list = []
    tokens = tokenizer.tokenize(line)

    for token in tokens:
        surface = token.surface

        # 英语
        if is_english(surface):
            token_list.append({'orig': surface, 'type': 1, 'pron': surface.lower()})

        # 汉字
        elif any(is_kanji(c) for c in surface):
            if token.phonetic == '*':
                print(f"---无法处理 {surface} ,尝试转换---")
                phonetic_items = kks.convert(surface)
                if phonetic_items and phonetic_items[0].get('hira'):
                    phonetic = phonetic_items[0]['hira']
                else:
                    token_list.append({'orig': surface, 'type': 0})
                    continue
            else:
                phonetic = "".join(item['hira'] for item in kks.convert(token.phonetic))

            if all(is_kanji(c) for c in surface):
                #print(f"  kanji:{surface}")
                prev_pron = None
                for ri in phonetic:
                    if ri == 'ー':
                        if not prev_pron:
                            print(f"---p无法处理长音符 {ri},前面的音节为 {prev_pron}---")
                            pi = None
                        else:
                            pi = prev_pron[-1].lower()
                    else:
                        pi = kks.convert(ri)[0]['hepburn']    
                        prev_pron = pi
                    token_list.append({'orig': surface, 'type': 2, 'pron': pi, 'ruby': ri})
                    surface = ''
            else:
                #print(f"  kanji/kana:{surface}")
                match_result = match_token(surface, phonetic)
                prev_pron = None
                for m_surface, m_phonetic in match_result:
                    if any(is_kanji(c) for c in m_surface):              
                        for ri in m_phonetic:
                            if ri == 'ー':
                                if not prev_pron:
                                    print(f"---m无法处理长音符 {ri},前面的音节为 {prev_pron}---")
                                    pi = None
                                else:
                                    pi = prev_pron[-1].lower()
                            else:
                                pi = kks.convert(ri)[0]['hepburn']                             
                                prev_pron = pi
                            token_list.append({'orig': m_surface, 'type': 2, 'pron': pi, 'ruby': ri})
                            m_surface = ''
                    else:
                        pi = kks.convert(m_surface)[0]['hepburn']
                        prev_pron = pi
                        token_list.append({'orig': m_surface, 'type': 3, 'pron': pi})

        # 假名
        elif any(is_kana(c) for c in surface):
            #print(f"  kana:{surface}")
            phonetic = "".join(item['hira'] for item in kks.convert(token.phonetic))
            if surface == phonetic:
                prev_pron = None
                for oi in surface:
                    pi = kks.convert(oi)[0]['hepburn']
                    token_list.append({'orig': oi, 'type': 3, 'pron': pi})
                    prev_pron = pi
            else:
                pron = kks.convert(phonetic)[0]['hepburn']
                token_list.append({'orig': surface, 'type': 3, 'pron': pron})

        # 其他字符
        else:
            #print(f"  other:{surface}")
            token_list.append({'orig': surface, 'type': 0})

    return token_list
