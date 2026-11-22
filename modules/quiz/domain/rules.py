from django.utils import timezone


def is_quiz_available(quiz, now=None):
    if now is None:
        now = timezone.now()
    if quiz.status != "AVAILABLE":
        return False
    if quiz.start_at and now < quiz.start_at:
        return False
    return not (quiz.close_at and now > quiz.close_at)


def can_attempt_quiz(quiz, current_attempts_count, now=None):
    if not is_quiz_available(quiz, now=now):
        return False, "Quiz is not currently available for attempts."
    if current_attempts_count >= quiz.max_attempts:
        return False, f"Maximum permitted attempts ({quiz.max_attempts}) reached."
    return True, ""


def can_edit_quiz(quiz):
    return quiz.status in ("DRAFT", "DRAFT_CONFIGURED", "READY_TO_PUBLISH")


def can_archive_quiz(quiz, active_attempts_count=0):
    if quiz.status != "CLOSED":
        return False, "Only closed quizzes may be archived."
    if active_attempts_count > 0:
        return False, "Cannot archive quiz with active student attempts."
    return True, ""
