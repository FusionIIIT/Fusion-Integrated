from modules.department.domain.announcements import is_complete, is_relevant


def test_is_complete_blank_title():
    """Tests is_complete when title is blank."""
    assert is_complete("", "some body", ["student"]) is False

def test_is_complete_blank_body():
    """Tests is_complete when body is blank."""
    assert is_complete("some title", "", ["student"]) is False

def test_is_complete_empty_roles():
    """Tests is_complete when target_roles is empty."""
    assert is_complete("some title", "some body", []) is False

def test_is_complete_unknown_role():
    """Tests is_complete when an unknown role is present."""
    assert is_complete("some title", "some body", ["student", "unknown_role"]) is False

def test_is_complete_good_case():
    """Tests is_complete with valid inputs."""
    assert is_complete("some title", "some body", ["student"]) is True
    assert is_complete("some title", "some body", ["faculty"]) is True
    assert is_complete("some title", "some body", ["student", "faculty"]) is True

def test_is_relevant_role_mismatch():
    """Tests is_relevant when viewer_kind is not in target_roles."""
    assert is_relevant(["student"], None, None, "faculty", None, None) is False

def test_is_relevant_faculty_on_role_alone():
    """Tests is_relevant when viewer is faculty and target_roles includes faculty."""
    assert is_relevant(["faculty"], None, None, "faculty", None, None) is True

def test_is_relevant_student_blank_targets():
    """Tests is_relevant when student viewer has blank targets (should pass if role matches)."""
    assert is_relevant(["student"], None, None, "student", None, None) is True

def test_is_relevant_programme_mismatch():
    """Tests is_relevant when student programme mismatches."""
    assert is_relevant(["student"], "prog_a", None, "student", "prog_b", None) is False

def test_is_relevant_batch_mismatch():
    """Tests is_relevant when student batch year mismatches."""
    assert is_relevant(["student"], None, 2022, "student", None, 2023) is False

def test_is_relevant_full_match():
    """Tests is_relevant when all student attributes match."""
    assert is_relevant(["student"], "prog_a", 2022, "student", "prog_a", 2022) is True
