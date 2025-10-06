from flask import flash, redirect, url_for, request
from flask_dance.consumer import OAuth2ConsumerBlueprint
from flask_login import current_user, login_user
from . import db
from .models import OAuth, User
import os
import json

def make_github_blueprint(app):
    os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'  # Only for development
    
    blueprint = OAuth2ConsumerBlueprint(
        "github",
        __name__,
        client_id=app.config.get("GITHUB_CLIENT_ID"),
        client_secret=app.config.get("GITHUB_CLIENT_SECRET"),
        scope=["user:email"],
        base_url="https://api.github.com/",
        token_url="https://github.com/login/oauth/access_token",
        authorization_url="https://github.com/login/oauth/authorize",
        token_url_params={"include_client_id": True}
    )

    @blueprint.before_app_request
    def set_oauth_token():
        if current_user.is_authenticated:
            oauth = OAuth.query.filter_by(
                provider="github",
                user_id=current_user.id,
            ).first()
            if oauth:
                try:
                    blueprint.token = json.loads(oauth.token)
                except (TypeError, json.JSONDecodeError):
                    blueprint.token = oauth.token

    @blueprint.route('/github/authorized')
    def github_authorized():
        if not blueprint.authorized:
            flash("Failed to log in with GitHub.", category="error")
            return redirect(url_for("auth.login"))

        resp = blueprint.session.get("/user")
        if not resp.ok:
            flash("Failed to get user info from GitHub.", category="error")
            return redirect(url_for("auth.login"))

        github_info = resp.json()
        github_user_id = str(github_info["id"])

        # Get user's email from GitHub
        emails_resp = blueprint.session.get("/user/emails")
        if not emails_resp.ok:
            flash("Failed to get email from GitHub.", category="error")
            return redirect(url_for("auth.login"))

        emails = emails_resp.json()
        primary_email = next(
            (email["email"] for email in emails if email["primary"]),
            emails[0]["email"] if emails else None
        )

        if not primary_email:
            flash("No email found in GitHub account.", category="error")
            return redirect(url_for("auth.login"))

        # Find existing OAuth token
        oauth = OAuth.query.filter_by(
            provider="github",
            provider_user_id=github_user_id
        ).first()

        if oauth:
            login_user(oauth.oauth_user)
            flash("Successfully signed in with GitHub.", category="success")
            return redirect(url_for("main.home"))

        # Find existing user by email
        user = User.query.filter_by(email=primary_email).first()
        if not user:
            # Create new user
            username = github_info.get("login")
            # Check if username exists
            if User.query.filter_by(username=username).first():
                username = f"{username}_{github_user_id}"
                
            user = User(
                username=username,
                email=primary_email,
                github_username=github_info.get("login"),
                avatar_url=github_info.get("avatar_url")
            )
            db.session.add(user)

        # Create OAuth token
        token_data = blueprint.token
        if isinstance(token_data, dict):
            token_data = json.dumps(token_data)

        oauth = OAuth(
            provider="github",
            provider_user_id=github_user_id,
            token=token_data,
            oauth_user=user
        )
        db.session.add(oauth)
        db.session.commit()

        login_user(user)
        flash("Successfully signed in with GitHub.", category="success")
        return redirect(url_for("main.home"))

    return blueprint
