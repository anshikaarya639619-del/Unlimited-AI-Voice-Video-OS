from app.core import split_text

def test_split_text_respects_limit():
    chunks = split_text(("This is a sentence. " * 100), 120)
    assert chunks
    assert all(0 < len(c) <= 120 for c in chunks)

def test_split_empty():
    assert split_text("   ") == []

def test_long_unbroken_token_is_split():
    chunks = split_text("x" * 300, 100)
    assert all(len(c) <= 100 for c in chunks)
