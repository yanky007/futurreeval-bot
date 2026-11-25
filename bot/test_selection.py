"""Keep smoke tests to exactly one question from the testing area."""


def select_test_question(questions, question_id=None):
    if not questions:
        raise ValueError("No open testing-area questions; no paid forecasts started")
    if question_id is None:
        return [questions[0]]
    for question in questions:
        if question.id_of_post == question_id:
            return [question]
    raise ValueError(
        f"Question {question_id} is not open in the testing area; no paid forecasts started"
    )
