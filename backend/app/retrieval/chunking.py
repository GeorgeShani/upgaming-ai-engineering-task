"""Character-preserving chunks measured with the embedding model's BPE tokenizer."""

import re
from bisect import bisect_left, bisect_right
from functools import lru_cache

import tiktoken

SIZE = 256
OVERLAP = 40


@lru_cache(maxsize=1)
def encoding():
    return tiktoken.get_encoding("cl100k_base")


def token_count(text):
    return len(encoding().encode(text, disallowed_special=()))


def fixed_spans(text, overlap=OVERLAP):
    tokens = encoding().encode(text, disallowed_special=())
    # BPE tokens can end halfway through a Unicode character. Only cut at boundaries
    # that are both token boundaries and character boundaries; never decode lossily.
    byte_to_char = {0: 0}
    byte_position = 0
    for position, char in enumerate(text, 1):
        byte_position += len(char.encode("utf-8"))
        byte_to_char[byte_position] = position
    boundaries = {0: 0}
    byte_position = 0
    for index, token in enumerate(tokens, 1):
        byte_position += len(encoding().decode_single_token_bytes(token))
        if byte_position in byte_to_char:
            boundaries[index] = byte_to_char[byte_position]
    keys = list(boundaries)
    start = 0
    while start < len(tokens):
        end_index = bisect_right(keys, min(start + SIZE, len(tokens))) - 1
        end = keys[end_index]
        while token_count(text[boundaries[start] : boundaries[end]]) > SIZE:
            end_index -= 1
            end = keys[end_index]
        yield boundaries[start], boundaries[end]
        if end == len(tokens):
            break
        start = keys[bisect_left(keys, max(start + 1, end - overlap))]


def sentence_spans(text):
    # A deterministic fallback for uploads, not a linguistic sentence classifier.
    # Dataset imports supply their original sentence boundaries instead.
    return [(m.start(), m.end()) for m in re.finditer(r"\S.*?(?:[.!?](?=\s|$)|$)", text)]


def chunk_spans(text, strategy, sentences=None):
    if strategy == "a":
        return list(fixed_spans(text))
    if strategy != "b":
        raise ValueError("Unknown chunking strategy")
    units = []
    for start, end in sentences or sentence_spans(text):
        units.extend((start + a, start + b) for a, b in fixed_spans(text[start:end], overlap=0))
    spans = []
    start = 0
    while start < len(units):
        end = start + 1
        while end < len(units) and token_count(text[units[start][0] : units[end][1]]) <= SIZE:
            end += 1
        spans.append((units[start][0], units[end - 1][1]))
        # Retain one sentence (or one oversized-sentence fragment) only if the next
        # group can also include new content. Otherwise advance without overlap.
        if end < len(units) and end - start > 1:
            if token_count(text[units[end - 1][0] : units[end][1]]) <= SIZE:
                start = end - 1
                continue
        start = end
    return spans
