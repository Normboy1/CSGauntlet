from celery_app import celery_app
from dataclasses import asdict
from backend.backend.ai_grader import AICodeGrader
from backend.backend.models import Problem, Submission, db
from flask import current_app
import asyncio

@celery_app.task
def grade_solution_task(submission_id):
    with celery_app.app.app_context():
        submission = Submission.query.get(submission_id)
        if not submission:
            current_app.logger.error(f"Submission with ID {submission_id} not found for grading.")
            return

        problem = Problem.query.get(submission.problem_id)
        if not problem:
            current_app.logger.error(f"Problem with ID {submission.problem_id} not found for submission {submission_id}.")
            return

        # Instantiate AICodeGrader within the task context
        ai_grader = AICodeGrader(
            openai_api_key=current_app.config['OPENAI_API_KEY'],
            openai_model=current_app.config.get('OPENAI_MODEL', 'gpt-4')
        )

        # Run the async grading function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            # Assuming problem.test_cases is a list of dicts
            # and problem.solution is the reference solution
            grading_result = loop.run_until_complete(
                ai_grader.grade_solution(
                    problem_description=problem.description,
                    solution_code=submission.code,
                    test_results=getattr(problem, "test_cases", {}),  # Safe fallback if not present
                    language="python",  # Assuming python for now, can be dynamic
                    reference_solution=problem.solution
                )
            )
        finally:
            loop.close()

        # Update submission with grading results
        submission.grading_result = asdict(grading_result)
        submission.points_earned = int(grading_result.criteria.total) # Update points based on AI grading
        db.session.commit()
        current_app.logger.info(f"Submission {submission_id} graded. Points: {submission.points_earned}")