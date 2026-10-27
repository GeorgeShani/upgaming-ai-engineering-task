from collections import Counter

from app.retrieval.chunking import chunk_spans, token_count
from app.retrieval.fusion import fuse


def test_fixed_windows_overlap_and_cover_unicode_without_corruption():
    text = ("ქართული ტექსტი 🚀 Payment router recovered. " * 120).strip()
    spans = chunk_spans(text, "a")
    assert len(spans) > 2 and spans[0][0] == 0 and spans[-1][1] == len(text)
    for start, end in spans:
        assert 0 < token_count(text[start:end]) <= 256
        assert "\ufffd" not in text[start:end]
    for (_, end), (start, _) in zip(spans, spans[1:], strict=False):
        assert start < end
        assert 35 <= token_count(text[start:end]) <= 42


def test_sentence_groups_preserve_overlap_and_split_oversized_sentences():
    sentences = [("A brief source sentence. " * 9).strip() for _ in range(15)]
    text = " ".join(sentences)
    ends = []
    pos = 0
    for sentence in sentences:
        ends.append((pos, pos + len(sentence)))
        pos += len(sentence) + 1
    spans = chunk_spans(text, "b", ends)
    assert len(spans) > 2
    assert all(token_count(text[start:end]) <= 256 for start, end in spans)
    assert spans[1][0] in [start for start, _ in ends]
    assert spans[1][0] < spans[0][1]
    huge = "repetition " * 1200
    pieces = chunk_spans(huge, "b", [(0, len(huge))])
    assert pieces[-1][1] == len(huge)
    assert all(token_count(huge[a:b]) <= 256 for a, b in pieces)


def test_rrf_deduplicates_each_ranking_then_caps_document_diversity():
    def hit(key, doc):
        return {"id": key, "payload": {"document_id": doc}, "score": 9999}

    dense = [hit("a", "one"), hit("a", "one"), hit("b", "one"), hit("c", "one")]
    sparse = [hit("b", "one"), hit("c", "one"), hit("d", "two")]
    ranked = fuse([dense, sparse])
    assert ranked[0]["id"] == "b"
    assert abs(ranked[0]["fusion_score"] - (1 / 62 + 1 / 61)) < 1e-12
    assert Counter(h["payload"]["document_id"] for h in ranked)["one"] == 2
    assert len({h["id"] for h in ranked}) == len(ranked)
    tied = fuse([[hit("z", "z")], [hit("a", "a")]])
    assert [h["id"] for h in tied] == ["a", "z"]
