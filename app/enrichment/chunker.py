from __future__ import annotations

import re

_CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
_WORD_RE = re.compile(r"[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)?")
_SENTENCE_BOUNDARY_RE = re.compile(r"(?<=[。！？.!?])\s+")


def chunk_text(text: str, *, max_tokens: int = 800) -> list[str]:
    """Split text into token-bounded chunks while keeping paragraphs intact when possible."""
    if max_tokens <= 0:
        raise ValueError("max_tokens must be positive")

    paragraphs = _split_paragraphs(text)
    chunks: list[str] = []
    current: list[str] = []
    current_tokens = 0

    for paragraph in paragraphs:
        paragraph_tokens = estimate_tokens(paragraph)
        if paragraph_tokens > max_tokens:
            if current:
                chunks.append("\n\n".join(current))
                current = []
                current_tokens = 0
            chunks.extend(_split_long_paragraph(paragraph, max_tokens=max_tokens))
            continue

        if current and current_tokens + paragraph_tokens > max_tokens:
            chunks.append("\n\n".join(current))
            current = []
            current_tokens = 0

        current.append(paragraph)
        current_tokens += paragraph_tokens

    if current:
        chunks.append("\n\n".join(current))

    return chunks


def estimate_tokens(text: str) -> int:
    """Estimate mixed Chinese/English token counts without requiring a tokenizer dependency."""
    normalized = " ".join(text.split())
    if not normalized:
        return 0

    cjk_count = len(_CJK_RE.findall(normalized))
    without_cjk = _CJK_RE.sub(" ", normalized)
    word_count = len(_WORD_RE.findall(without_cjk))
    return max(1, cjk_count + word_count)


def _split_paragraphs(text: str) -> list[str]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    raw_paragraphs = re.split(r"\n\s*\n+", normalized)
    paragraphs: list[str] = []
    for raw in raw_paragraphs:
        lines = [" ".join(line.split()) for line in raw.splitlines() if line.strip()]
        paragraph = " ".join(lines).strip()
        if paragraph:
            paragraphs.append(paragraph)
    return paragraphs


def _split_long_paragraph(paragraph: str, *, max_tokens: int) -> list[str]:
    sentences = [item.strip() for item in _SENTENCE_BOUNDARY_RE.split(paragraph) if item.strip()]
    if len(sentences) <= 1:
        return _split_by_tokens(paragraph, max_tokens=max_tokens)

    chunks: list[str] = []
    current: list[str] = []
    current_tokens = 0
    for sentence in sentences:
        sentence_tokens = estimate_tokens(sentence)
        if sentence_tokens > max_tokens:
            if current:
                chunks.append(" ".join(current))
                current = []
                current_tokens = 0
            chunks.extend(_split_by_tokens(sentence, max_tokens=max_tokens))
            continue
        if current and current_tokens + sentence_tokens > max_tokens:
            chunks.append(" ".join(current))
            current = []
            current_tokens = 0
        current.append(sentence)
        current_tokens += sentence_tokens
    if current:
        chunks.append(" ".join(current))
    return chunks


def _split_by_tokens(text: str, *, max_tokens: int) -> list[str]:
    pieces = re.findall(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]|[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)?|[^\s]", text)
    chunks: list[str] = []
    current: list[str] = []
    current_tokens = 0

    for piece in pieces:
        piece_tokens = estimate_tokens(piece)
        if current and current_tokens + piece_tokens > max_tokens:
            chunks.append(_join_token_pieces(current))
            current = []
            current_tokens = 0
        current.append(piece)
        current_tokens += piece_tokens

    if current:
        chunks.append(_join_token_pieces(current))
    return chunks


def _join_token_pieces(pieces: list[str]) -> str:
    text = ""
    previous_was_word = False
    for piece in pieces:
        is_word = bool(_WORD_RE.fullmatch(piece))
        if text and is_word and previous_was_word:
            text += " "
        text += piece
        previous_was_word = is_word
    return text.strip()
