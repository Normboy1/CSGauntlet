from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, current_app
from flask_login import login_required, current_user
from .models import User, Score, LanguageEnum, GameMode
from .models import User, Score, LanguageEnum, GameMode, Problem, Submission, db
from sqlalchemy import distinct
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, FileField, SubmitField
from wtforms.validators import DataRequired, Email
from flask_wtf.file import FileAllowed
from werkzeug.utils import secure_filename
import os
from datetime import datetime
from .auth import jwt_required
import asyncio
import time
import json
import subprocess
import tempfile
import docker

main = Blueprint('main', __name__)

@main.route('/health')
def health():
    return jsonify({"status": "ok"}), 200

class ProfileForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    college_name = StringField('College Name')
    university = StringField('University')
    github_username = StringField('GitHub Username')
    bio = TextAreaField('Bio')
    profile_photo = FileField('Profile Photo', validators=[FileAllowed(['jpg', 'jpeg', 'png', 'gif'])])
    college_logo = FileField('College Logo', validators=[FileAllowed(['jpg', 'jpeg', 'png', 'gif'])])
    submit = SubmitField('Update Profile')

@main.route('/')
def home():
    try:
        # Get top colleges by points
        top_colleges = db.session.query(
            User.college_name,
            db.func.sum(Score.is_win.cast(db.Integer)).label('wins'),
            db.func.count(Score.id).label('games'),
            (db.func.sum(Score.is_win.cast(db.Integer)) * 1000).label('points')
        ).join(Score, User.id == Score.user_id)\
         .group_by(User.college_name)\
         .order_by(db.desc('points'))\
         .limit(10)\
         .all()

        # Get top students by points
        top_students = db.session.query(
            User,
            db.func.sum(Score.is_win.cast(db.Integer)).label('points')
        ).join(Score, User.id == Score.user_id)\
         .group_by(User.id)\
         .order_by(db.desc('points'))\
         .limit(10)\
         .all()

        return render_template('home.html', 
                             top_colleges=top_colleges,
                             top_students=top_students)
    except Exception as e:
        # Log the error and render an error page or return a suitable response
        current_app.logger.error(f"Error fetching home page data: {e}")
        return render_template('error.html', message="Could not load home page data."), 500

@main.route('/game')
@login_required
def game():
    return render_template('game.html')

@main.route('/leaderboard')
def leaderboard():
    try:
        game_mode = request.args.get('game_mode', 'all')
        college = request.args.get('college', 'all')
        
        # Get all colleges for the filter
        colleges = db.session.query(
            User.college_name.distinct()
        ).filter(User.college_name != None)\
         .order_by(User.college_name)\
         .all()
        
        # Get college rankings
        college_rankings = db.session.query(
            User.college_name,
            db.func.sum(Score.is_win.cast(db.Integer)).label('points'),
            db.func.count(Score.id).label('games'),
            db.func.count(distinct(User.id)).label('active_players')
        ).join(Score, User.id == Score.user_id)\
         .group_by(User.college_name)\
         .order_by(db.desc('points'))\
         .all()
        
        # Get user rankings
        if college != 'all':
            user_rankings = db.session.query(
                User,
                db.func.sum(Score.is_win.cast(db.Integer)).label('points')
            ).join(Score, User.id == Score.user_id)\
             .filter(User.college_name == college)\
             .group_by(User.id)\
             .order_by(db.desc('points'))\
             .all()
        else:
            user_rankings = db.session.query(
                User,
                db.func.sum(Score.is_win.cast(db.Integer)).label('points')
            ).join(Score, User.id == Score.user_id)\
             .group_by(User.id)\
             .order_by(db.desc('points'))\
             .all()
        
        return render_template('leaderboard.html',
                             colleges=colleges,
                             college_rankings=college_rankings,
                             user_rankings=user_rankings,
                             selected_college=college)
    except Exception as e:
        current_app.logger.error(f"Error fetching leaderboard data: {e}")
        return render_template('error.html', message="Could not load leaderboard data."), 500

@main.route('/api/leaderboard')
def api_leaderboard():
    """JSON API endpoint for leaderboard data"""
    try:
        # Get user rankings with stats
        user_rankings = db.session.query(
            User,
            db.func.sum(Score.is_win.cast(db.Integer)).label('rating'),
            db.func.count(Score.id).label('games_played'),
            db.func.avg(Score.is_win.cast(db.Float)).label('win_rate')
        ).join(Score, User.id == Score.user_id)\
         .group_by(User.id)\
         .order_by(db.desc('rating'))\
         .limit(50)\
         .all()
        
        leaderboard_data = []
        for user, rating, games_played, win_rate in user_rankings:
            leaderboard_data.append({
                'username': user.username,
                'rating': int(rating) if rating else 0,
                'games_played': int(games_played) if games_played else 0,
                'win_rate': float(win_rate * 100) if win_rate else 0.0,
                'college': user.college_name or 'Unknown'
            })
        
        return jsonify(leaderboard_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@main.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = ProfileForm(obj=current_user)
    
    if form.validate_on_submit():
        try:
            # Handle profile photo upload
            if 'profile_photo' in request.files:
                photo = request.files['profile_photo']
                if photo.filename != '':
                    # Delete old photo if it's not the default
                    if current_user.profile_photo != 'default-avatar.png':
                        old_photo_path = os.path.join(main.root_path, 'static/uploads/profile_photos', current_user.profile_photo)
                        if os.path.exists(old_photo_path):
                            os.remove(old_photo_path)
                    
                    # Save new photo
                    photo_filename = f'user_{current_user.id}_{secure_filename(photo.filename)}'
                    photo_path = os.path.join(main.root_path, 'static/uploads/profile_photos', photo_filename)
                    photo.save(photo_path)
                    current_user.profile_photo = photo_filename

            # Handle college logo upload
            if 'college_logo' in request.files:
                logo = request.files['college_logo']
                if logo.filename != '':
                    # Delete old logo if it's not the default
                    if current_user.college_logo != 'default-college.png':
                        old_logo_path = os.path.join(main.root_path, 'static/uploads/college_logos', current_user.college_logo)
                        if os.path.exists(old_logo_path):
                            os.remove(old_logo_path)
                    
                    # Save new logo
                    logo_filename = f'college_{current_user.id}_{secure_filename(logo.filename)}'
                    logo_path = os.path.join(main.root_path, 'static/uploads/college_logos', logo_filename)
                    logo.save(logo_path)
                    current_user.college_logo = logo_filename

            # Update other profile fields
            form.populate_obj(current_user)
            db.session.commit()
            flash('Your profile has been updated!', 'success')
            return redirect(url_for('main.profile'))
        except Exception as e:
            current_app.logger.error(f"Error updating profile: {e}")
            flash('An error occurred while updating your profile.', 'danger')

    game_mode_stats = {
        'casual': current_user.get_stats('casual'),
        'ranked': current_user.get_stats('ranked'),
        'custom': current_user.get_stats('custom'),
        'all': current_user.get_stats()
    }
    
    return render_template('profile.html', user=current_user, form=form, game_mode_stats=game_mode_stats, game_modes=[mode.value for mode in GameMode])

@main.route('/api/profile')
@jwt_required
def api_profile():
    """JSON API endpoint for user profile data"""
    try:
        user = request.current_user
        
        # Get user stats
        stats = db.session.query(
            db.func.sum(Score.is_win.cast(db.Integer)).label('total_score'),
            db.func.count(Score.id).label('games_played'),
            db.func.avg(Score.is_win.cast(db.Float)).label('win_rate')
        ).filter(Score.user_id == user.id).first()
        
        # Get user rank
        user_rankings = db.session.query(
            User,
            db.func.sum(Score.is_win.cast(db.Integer)).label('rating')
        ).join(Score, User.id == Score.user_id)\
         .group_by(User.id)\
         .order_by(db.desc('rating'))\
         .all()
        
        user_rank = 1
        for rank_user, rating in user_rankings:
            if rank_user.id == user.id:
                break
            user_rank += 1
        
        profile_data = {
            'username': user.username,
            'email': user.email,
            'college': user.college_name or 'Unknown',
            'totalScore': int(stats.total_score) if stats.total_score else 0,
            'gamesPlayed': int(stats.games_played) if stats.games_played else 0,
            'winRate': float(stats.win_rate * 100) if stats.win_rate else 0.0,
            'rank': user_rank,
            'avatar_url': f'/static/uploads/profile_photos/{user.profile_photo}' if user.profile_photo else None,
            'github_username': user.github_username,
            'bio': user.bio,
            'university': user.university,
            'college_logo': f'/static/uploads/college_logos/{user.college_logo}' if user.college_logo else None
        }
        
        return jsonify(profile_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@main.route('/matchmaking')
@login_required
def matchmaking():
    try:
        return render_template('matchmaking.html')
    except Exception as e:
        current_app.logger.error(f"Error rendering matchmaking page: {e}")
        return render_template('error.html', message="Could not load matchmaking page."), 500

@main.route('/api/create_custom_game', methods=['POST'])
@jwt_required
def create_custom_game():
    """Create a new custom game"""
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'Request must contain JSON data'}), 400

        game_settings = data.get('settings', {})
        if not isinstance(game_settings, dict):
            return jsonify({'error': 'Settings must be a dictionary'}), 400

        user = request.current_user
        
        # Generate a unique game ID
        import uuid
        game_id = str(uuid.uuid4())
        
        # In a real implementation, you would store this in a database
        # For now, we'll return a mock response
        custom_game = {
            'id': game_id,
            'creator': user.username,
            'settings': game_settings,
            'status': 'waiting',
            'players': [user.username],
            'created_at': datetime.utcnow().isoformat()
        }
        
        return jsonify({
            'success': True,
            'game': custom_game
        })
    except Exception as e:
        current_app.logger.error(f"Error creating custom game: {e}")
        return jsonify({'error': str(e)}), 500

@main.route('/api/join_custom_game', methods=['POST'])
@jwt_required
def join_custom_game():
    """Join an existing custom game"""
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'Request must contain JSON data'}), 400

        game_id = data.get('game_id')
        if not game_id or not isinstance(game_id, str):
            return jsonify({'error': 'Game ID is required and must be a string'}), 400

        user = request.current_user
        
        # In a real implementation, you would validate the game exists
        # and add the user to the game
        return jsonify({
            'success': True,
            'message': f'Joined game {game_id}',
            'game_id': game_id
        })
    except Exception as e:
        current_app.logger.error(f"Error joining custom game: {e}")
        return jsonify({'error': str(e)}), 500

@main.route('/api/game_modes')
def get_game_modes():
    """Get available game modes"""
    try:
        game_modes = GameModeDetails.query.all()
        return jsonify({
            'success': True,
            'game_modes': [gm.to_dict() for gm in game_modes]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@main.route('/api/trivia/questions', methods=['GET'])
def get_trivia_questions():
    """Get trivia questions for the game"""
    try:
        difficulty = request.args.get('difficulty', 'all')
        count = int(request.args.get('count', 10))
        
        query = TriviaQuestion.query
        if difficulty != 'all':
            query = query.filter_by(difficulty=difficulty)
        
        trivia_questions = query.order_by(db.func.random()).limit(count).all()
        
        return jsonify({
            'success': True,
            'questions': [q.to_dict() for q in trivia_questions],
            'total_count': len(trivia_questions)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@main.route('/api/debug/challenges', methods=['GET'])
def get_debug_challenges():
    """Get debug challenges for the game"""
    try:
        difficulty = request.args.get('difficulty', 'all')
        count = int(request.args.get('count', 5))
        
        query = DebugChallenge.query
        if difficulty != 'all':
            query = query.filter_by(difficulty=difficulty)
        
        debug_challenges = query.order_by(db.func.random()).limit(count).all()
        
        return jsonify({
            'success': True,
            'challenges': [c.to_dict() for c in debug_challenges],
            'total_count': len(debug_challenges)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@main.route('/api/trivia/submit', methods=['POST'])
@jwt_required
def submit_trivia_answer():
    """Submit a trivia answer and get feedback"""
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'Request must contain JSON data'}), 400

        question_id = data.get('question_id')
        answer = data.get('answer')
        time_taken = data.get('time_taken', 0)

        if not question_id:
            return jsonify({'error': 'Question ID is required'}), 400
        if not isinstance(answer, (str, int, float, bool, list, dict)):
            return jsonify({'error': 'Answer is required and must be a valid JSON type'}), 400
        if not isinstance(time_taken, (int, float)) or time_taken < 0:
            return jsonify({'error': 'Time taken must be a non-negative number'}), 400
        
        # In a real implementation, you would:
        # 1. Validate the answer against the database
        # 2. Calculate points based on difficulty, time, streak
        # 3. Update user stats
        # 4. Store the submission
        
        # For demo purposes, we'll simulate correct/incorrect
        is_correct = True  # This would be determined by actual answer validation
        points_earned = 20 if is_correct else 0
        
        return jsonify({
            'success': True,
            'correct': is_correct,
            'points_earned': points_earned,
            'explanation': 'Great job! Your answer is correct.'
        })
    except Exception as e:
        current_app.logger.error(f"Error submitting trivia answer: {e}")
        return jsonify({'error': str(e)}), 500

@main.route('/api/debug/submit', methods=['POST'])
@jwt_required
def submit_debug_fix():
    """Submit a debug fix and get feedback"""
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'Request must contain JSON data'}), 400

        challenge_id = data.get('challenge_id')
        bug_id = data.get('bug_id')
        fix = data.get('fix')
        time_taken = data.get('time_taken', 0)

        if not challenge_id:
            return jsonify({'error': 'Challenge ID is required'}), 400
        if not bug_id:
            return jsonify({'error': 'Bug ID is required'}), 400
        if not fix or not isinstance(fix, str):
            return jsonify({'error': 'Fix is required and must be a string'}), 400
        if not isinstance(time_taken, (int, float)) or time_taken < 0:
            return jsonify({'error': 'Time taken must be a non-negative number'}), 400
        
        # In a real implementation, you would:
        # 1. Validate the fix against the expected solution
        # 2. Calculate points based on difficulty, time, hints used
        # 3. Update user stats
        # 4. Store the submission
        
        # For demo purposes, we'll simulate correct/incorrect
        is_correct = True  # This would be determined by actual fix validation
        points_earned = 25 if is_correct else 0
        
        return jsonify({
            'success': True,
            'correct': is_correct,
            'points_earned': points_earned,
            'feedback': 'Excellent! Your fix is correct.'
        })
    except Exception as e:
        current_app.logger.error(f"Error submitting debug fix: {e}")
        return jsonify({'error': str(e)}), 500

@main.route('/update_score', methods=['POST'])
@jwt_required
def update_score():
    try:
        data = request.json
        language = data.get('language')
        is_win = data.get('is_win')
        game_mode = data.get('game_mode')
        user = request.current_user

        score = Score(
            user_id=user.id,
            language=language,
            is_win=is_win,
            game_mode=GameMode(game_mode)
        )
        db.session.add(score)
        db.session.commit()
        
        return {'success': True}
    except Exception as e:
        current_app.logger.error(f"Error updating score: {e}")
        return jsonify({'error': str(e)}), 500

@main.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    form = ProfileForm(obj=current_user)
    
    if form.validate_on_submit():
        # Handle profile photo upload
        if 'profile_photo' in request.files:
            photo = request.files['profile_photo']
            if photo.filename != '':
                # Delete old photo if it's not the default
                if current_user.profile_photo != 'default-avatar.png':
                    old_photo_path = os.path.join(main.root_path, 'static/uploads/profile_photos', current_user.profile_photo)
                    if os.path.exists(old_photo_path):
                        os.remove(old_photo_path)
                
                # Save new photo
                photo_filename = f'user_{current_user.id}_{secure_filename(photo.filename)}'
                photo_path = os.path.join(main.root_path, 'static/uploads/profile_photos', photo_filename)
                photo.save(photo_path)
                current_user.profile_photo = photo_filename

        # Handle college logo upload
        if 'college_logo' in request.files:
            logo = request.files['college_logo']
            if logo.filename != '':
                # Delete old logo if it's not the default
                if current_user.college_logo != 'default-college.png':
                    old_logo_path = os.path.join(main.root_path, 'static/uploads/college_logos', current_user.college_logo)
                    if os.path.exists(old_logo_path):
                        os.remove(old_logo_path)
                
                # Save new logo
                logo_filename = f'college_{current_user.id}_{secure_filename(logo.filename)}'
                logo_path = os.path.join(main.root_path, 'static/uploads/college_logos', logo_filename)
                logo.save(logo_path)
                current_user.college_logo = logo_filename

        # Update other profile fields
        form.populate_obj(current_user)
        db.session.commit()
        flash('Your profile has been updated!', 'success')
        return redirect(url_for('main.profile'))

    return render_template('profile.html', user=current_user, form=form)

@main.route('/api/upload_avatar', methods=['POST'])
@jwt_required
def upload_avatar():
    try:
        user = request.current_user
        if 'avatar' not in request.files or request.files['avatar'].filename == '':
            return jsonify({'error': 'No file uploaded.'}), 400
        file = request.files['avatar']
        
        # Only allow certain extensions
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
        ext = file.filename.rsplit('.', 1)[-1].lower()
        if ext not in allowed_extensions:
            return jsonify({'error': f'Invalid file type. Allowed types are: {", ".join(allowed_extensions)}'}), 400
        
        # Save file
        filename = f'user_{user.id}_{secure_filename(file.filename)}'
        upload_dir = os.path.join(current_app.root_path, 'static/uploads/profile_photos')
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, filename)
        file.save(file_path)
        user.profile_photo = filename
        db.session.commit()
        return jsonify({'success': True, 'avatar_url': f'/static/uploads/profile_photos/{filename}'}), 200
    except Exception as e:
        current_app.logger.error(f"Error uploading avatar: {e}")
        return jsonify({'error': str(e)}), 500

@main.route('/api/code/submit_with_grading', methods=['POST'])
@jwt_required
def submit_code_with_ai_grading():
    """Submit code solution and get comprehensive AI grading"""
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'Request must contain JSON data'}), 400

        code = data.get('code', '')
        problem_id = data.get('problem_id')
        language = data.get('language', 'python')
        
        if not code.strip() or not isinstance(code, str):
            return jsonify({'error': 'Code is required and must be a string'}), 400
        if not problem_id or not isinstance(problem_id, (int, str)):
            return jsonify({'error': 'Problem ID is required and must be an integer or string'}), 400
        if not language or not isinstance(language, str):
            return jsonify({'error': 'Language is required and must be a string'}), 400
        
        # Get problem details (this would normally come from database)
        problem = get_problem_by_id(problem_id)  # You'd implement this
        if not problem:
            return jsonify({'error': 'Problem not found'}), 404
        
        # Execute and grade the code
        from .code_executor import CodeExecutor
        executor = CodeExecutor()
        
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            success, message, test_results, grading_result = loop.run_until_complete(
                executor.validate_and_grade_solution(code, problem)
            )
        finally:
            loop.close()
        
        # Calculate points based on grading
        base_points = 100
        quality_multiplier = grading_result.criteria.total / 100
        final_points = int(base_points * quality_multiplier)
        
        # Store submission in database (implement as needed)
        submission_id = store_code_submission(
            user_id=request.current_user.id,
            problem_id=problem_id,
            code=code,
            grading_result=grading_result,
            points=final_points
        )
        
        return jsonify({
            'success': True,
            'submission_id': submission_id,
            'test_results': test_results,
            'grading': {
                'criteria': {
                    'correctness': grading_result.criteria.correctness,
                    'efficiency': grading_result.criteria.efficiency,
                    'readability': grading_result.criteria.readability,
                    'style': grading_result.criteria.style,
                    'innovation': grading_result.criteria.innovation,
                    'total': grading_result.criteria.total
                },
                'feedback': grading_result.feedback,
                'suggestions': grading_result.suggestions,
                'code_smells': grading_result.code_smells,
                'best_practices': grading_result.best_practices,
                'overall_grade': grading_result.overall_grade,
                'rank_percentile': grading_result.rank_percentile,
                'complexity_analysis': grading_result.complexity_analysis,
                'memory_efficiency': grading_result.memory_efficiency
            },
            'points_earned': final_points,
            'message': message
        })
        
    except Exception as e:
        current_app.logger.error(f"Error submitting code with AI grading: {e}")
        return jsonify({'error': str(e)}), 500

@main.route('/api/code/compare_solutions', methods=['POST'])
@jwt_required
def compare_solutions():
    """Compare multiple solutions and rank them"""
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'Request must contain JSON data'}), 400

        solutions = data.get('solutions', [])
        problem_id = data.get('problem_id')

        if not isinstance(solutions, list):
            return jsonify({'error': 'Solutions must be a list'}), 400
        if len(solutions) < 2:
            return jsonify({'error': 'At least 2 solutions required for comparison'}), 400
        for i, solution in enumerate(solutions):
            if not isinstance(solution, dict):
                return jsonify({'error': f'Solution at index {i} must be a dictionary'}), 400
            if 'code' not in solution or not isinstance(solution['code'], str):
                return jsonify({'error': f'Solution at index {i} must contain a "code" string'}), 400
            if 'user_id' not in solution or not isinstance(solution['user_id'], (str, int)):
                return jsonify({'error': f'Solution at index {i} must contain a "user_id" (string or integer)'}), 400
        
        if not problem_id or not isinstance(problem_id, (int, str)):
            return jsonify({'error': 'Problem ID is required and must be an integer or string'}), 400
        
        problem = get_problem_by_id(problem_id)
        if not problem:
            return jsonify({'error': 'Problem not found'}), 404
        
        from .code_executor import CodeExecutor
        executor = CodeExecutor()
        
        graded_solutions = []
        
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            for i, solution in enumerate(solutions):
                success, message, test_results, grading_result = loop.run_until_complete(
                    executor.validate_and_grade_solution(solution['code'], problem)
                )
                
                graded_solutions.append({
                    'user_id': solution.get('user_id', f'user_{i}'),
                    'code': solution['code'],
                    'success': success,
                    'total_score': grading_result.criteria.total,
                    'grade': grading_result.overall_grade,
                    'percentile': grading_result.rank_percentile,
                    'criteria': {
                        'correctness': grading_result.criteria.correctness,
                        'efficiency': grading_result.criteria.efficiency,
                        'readability': grading_result.criteria.readability,
                        'style': grading_result.criteria.style,
                        'innovation': grading_result.criteria.innovation
                    },
                    'feedback': grading_result.feedback
                })
        finally:
            loop.close()
        
        # Sort by total score (highest first)
        graded_solutions.sort(key=lambda x: x['total_score'], reverse=True)
        
        # Add rankings
        for i, solution in enumerate(graded_solutions):
            solution['rank'] = i + 1
            
        return jsonify({
            'success': True,
            'ranked_solutions': graded_solutions,
            'winner': graded_solutions[0] if graded_solutions else None
        })
        
    except Exception as e:
        current_app.logger.error(f"Error comparing solutions: {e}")
        return jsonify({'error': str(e)}), 500

@main.route('/api/leaderboard/detailed', methods=['GET'])
@jwt_required  
def get_detailed_leaderboard():
    """Get leaderboard with detailed statistics"""
    try:
        time_period = request.args.get('period', 'all')  # all, week, month
        problem_type = request.args.get('type', 'all')   # all, algorithms, data_structures
        
        leaderboard_data = get_leaderboard_with_stats(time_period, problem_type)
        
        return jsonify({
            'success': True,
            'leaderboard': leaderboard_data,
            'period': time_period,
            'type': problem_type
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@main.route('/api/problems', methods=['GET'])
def get_coding_problems():
    """Get available coding problems with difficulty and metadata"""
    try:
        difficulty = request.args.get('difficulty', 'all')
        topic = request.args.get('topic', 'all')
        
        query = Problem.query
        if difficulty != 'all':
            query = query.filter_by(difficulty=difficulty)
        # Assuming 'topic' field exists in Problem model
        if topic != 'all':
            query = query.filter_by(topic=topic)
        
        problems = query.all()
        
        return jsonify({
            'success': True,
            'problems': [p.to_dict() for p in problems],
            'total_count': len(problems)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Helper functions (implement these based on your database schema)
def get_problem_by_id(problem_id):
    """Get problem details by ID from database"""
    return Problem.query.get(problem_id)

def store_code_submission(user_id, problem_id, code, grading_result, points):
    """Store code submission with grading results in database"""
    submission = Submission(
        user_id=user_id,
        problem_id=problem_id,
        code=code,
        grading_result=grading_result,
        points_earned=points
    )
    db.session.add(submission)
    db.session.commit()
    return submission.id

def get_leaderboard_with_stats(time_period, problem_type):
    """Get leaderboard with detailed statistics"""
    query = db.session.query(
        User.username,
        User.college_name,
        db.func.sum(Submission.points_earned).label('total_points'),
        db.func.count(Submission.id).label('problems_solved')
    ).join(Submission, User.id == Submission.user_id)

    if time_period != 'all':
        # Implement time period filtering (e.g., last week, last month)
        # For simplicity, this example doesn't implement full time filtering
        pass

    if problem_type != 'all':
        # Implement problem type filtering (e.g., algorithms, data_structures)
        # This would require adding a 'topic' or 'category' field to the Problem model
        # and joining with it.
        pass

    leaderboard_data = query.group_by(User.id, User.username, User.college_name)\
                            .order_by(db.desc('total_points'))\
                            .limit(50)\
                            .all()

    formatted_leaderboard = []
    for username, college_name, total_points, problems_solved in leaderboard_data:
        formatted_leaderboard.append({
            'username': username,
            'college': college_name or 'Unknown',
            'total_points': int(total_points) if total_points else 0,
            'problems_solved': int(problems_solved) if problems_solved else 0,
            'average_grade': 'N/A',  # Requires more complex calculation from grading_result JSON
            'avg_score': 0.0,      # Requires more complex calculation from grading_result JSON
            'best_categories': [], # Requires more complex calculation from grading_result JSON
            'streak': 0,           # Requires dedicated logic
            'efficiency_rating': 0.0,
            'style_rating': 0.0
        })
    return formatted_leaderboard
