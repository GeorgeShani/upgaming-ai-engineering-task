from urllib.parse import quote

from .models import Document, EvaluationCase, Evidence, Source
from .models import make_document as document_from_sentences


def context_documents(row: dict, revision: str, split: str) -> list[Document]:
    context = row["context"]
    titles, paragraphs = context["title"], context["sentences"]
    if len(titles) != len(paragraphs):
        raise ValueError("HotpotQA context title/sentence arrays have different lengths")
    return [
        document_from_sentences(
            title,
            sentences,
            Source(
                kind="hotpotqa",
                revision=revision,
                split=split,
                record_id=row["id"],
                url=f"https://en.wikipedia.org/wiki/{quote(title.replace(' ', '_'), safe='')}",
                license="CC-BY-SA-4.0",
            ),
        )
        for title, sentences in zip(titles, paragraphs, strict=True)
    ]


def labelled_case(
    row: dict, revision: str, split: str, case_id: str
) -> tuple[EvaluationCase, list[Document]]:
    documents = context_documents(row, revision, "validation")
    by_title = dict(zip(row["context"]["title"], documents, strict=True))
    support = row["supporting_facts"]
    evidence = []
    selected = {}
    for title, sentence_id in zip(support["title"], support["sent_id"], strict=True):
        doc = by_title[title]
        sentence = next(s for s in doc.segments if s.sentence_id == sentence_id)
        evidence.append(
            Evidence(document_id=doc.document_id, sentence_id=sentence_id, quote=sentence.text)
        )
        selected[doc.document_id] = doc
    return EvaluationCase(
        case_id=case_id,
        category=row["type"],
        split=split,
        question=row["question"],
        expected_status="answered",
        gold_answer=row["answer"],
        evidence=evidence,
        source_question_id=row["id"],
    ), list(selected.values())


def stream_rows(revision: str, split: str):
    # This optional, heavy dependency is only needed by offline preparation, not the web app.
    from datasets import load_dataset

    return load_dataset(
        "hotpotqa/hotpot_qa",
        "distractor",
        revision=revision,
        split=split,
        streaming=True,
        token=False,
    )
