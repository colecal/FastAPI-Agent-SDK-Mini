from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple


WORD_RE = re.compile(r"[A-Za-z0-9_]+")


def tokenize(text: str) -> List[str]:
    return [t.lower() for t in WORD_RE.findall(text)]


@dataclass
class Doc:
    doc_id: str
    title: str
    text: str


class TinyRetriever:
    """A tiny offline retriever (TF*IDF-ish) over a local corpus folder."""

    def __init__(self, corpus_dir: str = "data/corpus"):
        self.corpus_dir = Path(corpus_dir)
        self.docs: List[Doc] = []
        self._doc_tf: List[Counter[str]] = []
        self._df: Counter[str] = Counter()
        self._load()

    def _load(self) -> None:
        self.docs.clear()
        self._doc_tf.clear()
        self._df.clear()

        for p in sorted(self.corpus_dir.glob("*.txt")):
            text = p.read_text(encoding="utf-8")
            title = p.stem.replace("_", " ")
            doc = Doc(doc_id=p.name, title=title, text=text)
            tf = Counter(tokenize(text))
            self.docs.append(doc)
            self._doc_tf.append(tf)
            for term in tf.keys():
                self._df[term] += 1

    def search(self, query: str, k: int = 3) -> List[Tuple[Doc, float]]:
        q_terms = tokenize(query)
        if not q_terms or not self.docs:
            return []

        N = len(self.docs)
        q_tf = Counter(q_terms)

        def idf(term: str) -> float:
            df = self._df.get(term, 0)
            return math.log((N + 1) / (df + 1)) + 1.0

        q_vec = {t: q_tf[t] * idf(t) for t in q_tf}

        scored: List[Tuple[int, float]] = []
        for i, tf in enumerate(self._doc_tf):
            # dot product
            dot = 0.0
            for t, w in q_vec.items():
                dot += w * (tf.get(t, 0) * idf(t))
            # norm
            norm_d = math.sqrt(sum((tf.get(t, 0) * idf(t)) ** 2 for t in q_vec.keys())) or 1.0
            norm_q = math.sqrt(sum(w ** 2 for w in q_vec.values())) or 1.0
            score = dot / (norm_q * norm_d)
            scored.append((i, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        out: List[Tuple[Doc, float]] = []
        for i, s in scored[:k]:
            if s <= 0:
                continue
            out.append((self.docs[i], float(s)))
        return out
