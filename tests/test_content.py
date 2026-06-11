from content.days import DAYS


def test_days_has_48_entries():
    assert len(DAYS) == 48


def test_each_day_has_required_keys():
    required = {"day", "title", "week", "phase", "topic", "estimated_minutes", "sections", "key_terms"}
    for d in DAYS:
        missing = required - d.keys()
        assert not missing, f"Day {d.get('day')} missing: {missing}"


def test_day_numbers_are_sequential():
    numbers = [d["day"] for d in DAYS]
    assert numbers == list(range(1, 49))


def test_each_day_has_at_least_one_section():
    for d in DAYS:
        assert len(d["sections"]) >= 1, f"Day {d['day']} has no sections"


def test_each_section_has_required_keys():
    for d in DAYS:
        for s in d["sections"]:
            assert "heading" in s, f"Day {d['day']} section missing 'heading'"
            assert "body" in s, f"Day {d['day']} section missing 'body'"


from content.questions import QUESTIONS

def test_questions_covers_days_2_to_48():
    days_covered = {q["day"] for q in QUESTIONS}
    for d in range(2, 49):
        assert d in days_covered, f"Day {d} has no questions in questions.py"

def test_each_question_has_required_keys():
    required = {"id", "day", "topic", "difficulty", "question", "options", "answer", "explanation"}
    for q in QUESTIONS:
        missing = required - q.keys()
        assert not missing, f"Question {q.get('id')} missing: {missing}"

def test_each_question_has_four_options():
    for q in QUESTIONS:
        assert set(q["options"].keys()) == {"A", "B", "C", "D"}, f"{q['id']} bad options"

def test_answer_is_valid_option():
    for q in QUESTIONS:
        assert q["answer"] in {"A", "B", "C", "D"}, f"{q['id']} invalid answer: {q['answer']}"

def test_difficulty_values():
    valid = {"basic", "intermediate", "advanced"}
    for q in QUESTIONS:
        assert q["difficulty"] in valid, f"{q['id']} bad difficulty: {q['difficulty']}"

def test_topic_matches_days_topic():
    from content.days import DAYS
    day_topics = {d["day"]: d["topic"] for d in DAYS}
    for q in QUESTIONS:
        expected = day_topics.get(q["day"])
        assert q["topic"] == expected, (
            f"Question {q['id']} topic '{q['topic']}' != day {q['day']} topic '{expected}'"
        )


from content.loader import get_day_content, get_day_questions

def test_get_day_content_returns_dict_for_all_days():
    for day_num in range(1, 49):
        content = get_day_content(day_num)
        assert isinstance(content, dict), f"Day {day_num} content not a dict"
        assert "sections" in content

def test_get_day_questions_returns_list_for_all_days():
    for day_num in range(1, 49):
        qs = get_day_questions(day_num)
        assert isinstance(qs, list), f"Day {day_num} questions not a list"
        assert len(qs) > 0, f"Day {day_num} has no questions"

def test_get_day_content_day1_uses_docx_when_present():
    content = get_day_content(1)
    assert len(content["sections"]) > 0

def test_get_day_questions_day1_returns_questions():
    qs = get_day_questions(1)
    assert len(qs) >= 10
    for q in qs:
        assert "question" in q
        assert "answer" in q
        assert "options" in q
