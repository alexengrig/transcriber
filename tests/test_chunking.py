from transcriber.engines.chunking import plan_chunks


def test_merges_close_spans_up_to_limit():
    out = plan_chunks([(0, 5), (5.5, 12), (12.2, 19), (19.5, 25)], max_len=20, pad=0)
    assert out == [(0, 19), (19.5, 25)]


def test_splits_overlong_span():
    out = plan_chunks([(0, 45)], max_len=20, pad=0)
    assert len(out) == 3 and all(b - a <= 20 for a, b in out)


def test_pad_is_clamped_to_total():
    assert plan_chunks([(0.05, 9.95)], pad=0.15, total=10.0) == [(0.0, 10.0)]


def test_split_phrases_on_punctuation_and_pause():
    from transcriber.engines.chunking import split_phrases

    words = [(0, 0.5, "Привет,"), (0.6, 1.0, "мир."), (1.1, 1.5, "Как"), (3.0, 3.4, "дела?")]
    assert split_phrases(words) == [
        (0, 1.0, "Привет, мир."), (1.1, 1.5, "Как"), (3.0, 3.4, "дела?"),
    ]
