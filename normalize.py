from janome.tokenizer import Tokenizer
import pykakasi
import re

kks = pykakasi.kakasi()
tokenizer = Tokenizer()

def is_english(text):
    return bool(re.match(r'^[a-zA-Z]+$', text))

def is_kanji(char):
    return ('\u4E00' <= char <= '\u9FFF' or '\u3400' <= char <= '\u4DBF' or
            '\uF900' <= char <= '\uFAFF' or char == '\u3005')

def is_hiragana(char):
    return '\u3040' <= char <= '\u309F'

def is_katakana(char):
    return '\u30A0' <= char <= '\u30FF'

def is_kana(char):
    if char in ['・', '゠', 'ー']:
        return False
    return is_hiragana(char) or is_katakana(char)

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

def get_vowel_for_chouon(prev_phonetic):
    vowel_map = {
        # あ行
        'a': 'a', 'ka': 'a', 'ga': 'a', 'sa': 'a', 'za': 'a', 'ta': 'a', 'da': 'a',
        'na': 'a', 'ha': 'a', 'ba': 'a', 'pa': 'a', 'ma': 'a', 'ya': 'a', 'ra': 'a', 'wa': 'a',
        # い行
        'i': 'i', 'ki': 'i', 'gi': 'i', 'shi': 'i', 'ji': 'i', 'chi': 'i', 'di': 'i',
        'ni': 'i', 'hi': 'i', 'bi': 'i', 'pi': 'i', 'mi': 'i', 'ri': 'i',
        # う行
        'u': 'u', 'ku': 'u', 'gu': 'u', 'su': 'u', 'zu': 'u', 'tsu': 'u', 'du': 'u',
        'nu': 'u', 'fu': 'u', 'bu': 'u', 'pu': 'u', 'mu': 'u', 'yu': 'u', 'ru': 'u',
        # え行
        'e': 'e', 'ke': 'e', 'ge': 'e', 'se': 'e', 'ze': 'e', 'te': 'e', 'de': 'e',
        'ne': 'e', 'he': 'e', 'be': 'e', 'pe': 'e', 'me': 'e', 're': 'e',
        # お行
        'o': 'o', 'ko': 'o', 'go': 'o', 'so': 'o', 'zo': 'o', 'to': 'o', 'do': 'o',
        'no': 'o', 'ho': 'o', 'bo': 'o', 'po': 'o', 'mo': 'o', 'yo': 'o', 'ro': 'o'
    }
    return vowel_map.get(prev_phonetic.lower())

def process_line(line):
    token_list = []
    tokens = tokenizer.tokenize(line)

    for token in tokens:
        surface = token.surface

        # 英语
        if is_english(surface):
            #print(f"  english:{surface}")
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
                        vowel = get_vowel_for_chouon(prev_pron)
                        token_list.append({'orig': surface, 'type': 2, 'pron': vowel, 'ruby': ri})
                    else:
                        pi = kks.convert(ri)[0]['hepburn']
                        token_list.append({'orig': surface, 'type': 2, 'pron': pi, 'ruby': ri})
                        prev_pron = pi
                    surface = ''
            else:
                #print(f"  kanji/kana:{surface}")
                match_result = match_token(surface, phonetic)
                for m_surface, m_phonetic in match_result:
                    if any(is_kanji(c) for c in m_surface):
                        prev_pron = None
                        for ri in m_phonetic:
                            if ri == 'ー':
                                vowel = get_vowel_for_chouon(prev_pron)
                                if vowel:
                                    token_list.append({'orig': m_surface, 'type': 2, 'pron': vowel, 'ruby': ri})
                                else:
                                    print(f"---无法处理长音符 {ri}，前面的音节为 {prev_pron}---")
                                    continue
                            else:
                                pi = kks.convert(ri)[0]['hepburn']
                                token_list.append({'orig': m_surface, 'type': 2, 'pron': pi, 'ruby': ri})
                                prev_pron = pi
                                m_surface = ''
                    else:
                        pi = kks.convert(m_surface)[0]['hepburn']
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