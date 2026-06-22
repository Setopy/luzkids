from app import get_rank, xp_for_lesson, RANKS


def test_get_rank_zero_xp_is_seeker():
    threshold, name, emoji = get_rank(0)
    assert name == "Seeker"


def test_get_rank_exact_threshold():
    threshold, name, emoji = get_rank(300)
    assert name == "Growing"


def test_get_rank_between_thresholds_picks_lower():
    # 599 is one below the Sanctified threshold (600)
    threshold, name, emoji = get_rank(599)
    assert name == "Growing"


def test_get_rank_highest():
    threshold, name, emoji = get_rank(999999)
    assert name == RANKS[-1][1]


def test_xp_for_lesson_base_only():
    assert xp_for_lesson(quiz_score=None, total_q=0) == 50


def test_xp_for_lesson_perfect_quiz_bonus():
    assert xp_for_lesson(quiz_score=5, total_q=5) == 75


def test_xp_for_lesson_imperfect_quiz_no_bonus():
    assert xp_for_lesson(quiz_score=4, total_q=5) == 50
