from dimarch_scribe.transcription.segments import Segment, dedupe_chunk_boundary, parse_segments


def test_parse_segments_basic():
    raw = (
        "[00:00:00.000 --> 00:00:02.500]   hello world\n"
        "[00:00:02.500 --> 00:00:05.000]   (speaker 0) second segment\n"
    )
    segments = parse_segments(raw)
    assert len(segments) == 2
    assert segments[0].text == "hello world"
    assert segments[0].speaker is None
    assert segments[1].text == "second segment"
    assert segments[1].speaker == "0"
    assert segments[1].start == 2.5


def test_parse_segments_skips_non_matching_lines():
    raw = "not a segment line\n[00:00:00.000 --> 00:00:01.000]   real segment\n"
    segments = parse_segments(raw)
    assert len(segments) == 1
    assert segments[0].text == "real segment"


def test_dedupe_chunk_boundary_removes_content_word_duplicate():
    # real case found during v0.2 acceptance testing (webinar, chunk 5->6)
    prev_text = "потому что, если нет готовности..."
    seg = Segment(start=1800.0, end=1808.36, speaker=None,
                  text="готовности. Да, сейчас, Саша, я договорю, пожалуйста.")
    dedupe_chunk_boundary(prev_text, seg)
    assert seg.text == "Да, сейчас, Саша, я договорю, пожалуйста."


def test_dedupe_chunk_boundary_removes_second_confirmed_case():
    # real case found during v0.2 acceptance testing (monologue, chunk 1->2)
    prev_text = "да я подписал за несколько лет около 200 человек"
    seg = Segment(start=600.0, end=605.0, speaker=None,
                  text="человек и из них было человек 5 это именно близкие родственники")
    dedupe_chunk_boundary(prev_text, seg)
    assert seg.text == "и из них было человек 5 это именно близкие родственники"


def test_dedupe_chunk_boundary_preserves_filler_word_repeat():
    # "вот" is a common discourse marker that legitimately repeats in
    # spontaneous speech — must NOT be stripped (verbatim guarantee)
    prev_text = "И вы можете точно так же продавать его. Вот представьте вот"
    seg = Segment(start=0, end=1, speaker=None, text="вот эта обложка, это сделано точно так же")
    dedupe_chunk_boundary(prev_text, seg)
    assert seg.text == "вот эта обложка, это сделано точно так же"


def test_dedupe_chunk_boundary_preserves_genuine_repeated_name():
    # a deliberately-repeated placeholder example name must survive
    prev_text = "ребят, в конце я рекомендую снова написать там Анна Иванова,"
    seg = Segment(start=0, end=1, speaker=None,
                  text="Анна Иванова можно указать свои соцсети еще можно")
    # "Анна" != last word "Анна Иванова," (multi-word) so the single-word
    # match check naturally doesn't fire here; confirms no false positive
    # on a multi-word repeated phrase.
    dedupe_chunk_boundary(prev_text, seg)
    assert seg.text == "Анна Иванова можно указать свои соцсети еще можно"


def test_dedupe_chunk_boundary_noop_when_no_match():
    prev_text = "текст заканчивается словом яблоко"
    seg = Segment(start=0, end=1, speaker=None, text="груша это другое слово")
    dedupe_chunk_boundary(prev_text, seg)
    assert seg.text == "груша это другое слово"


def test_dedupe_chunk_boundary_noop_on_empty_inputs():
    seg = Segment(start=0, end=1, speaker=None, text="")
    dedupe_chunk_boundary("что-то", seg)
    assert seg.text == ""

    seg2 = Segment(start=0, end=1, speaker=None, text="слово")
    dedupe_chunk_boundary("", seg2)
    assert seg2.text == "слово"


def test_dedupe_chunk_boundary_case_insensitive():
    prev_text = "и это было слово Готовности"
    seg = Segment(start=0, end=1, speaker=None, text="готовности продолжение фразы")
    dedupe_chunk_boundary(prev_text, seg)
    assert seg.text == "продолжение фразы"
