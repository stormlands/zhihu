from datetime import datetime
from flask import render_template, redirect, url_for, current_app, abort, flash, request, make_response
from flask_login import current_user, login_required
from flask_sqlalchemy import get_debug_queries
from . import main
from .forms import PostForm, EditProfileForm, EditProfileAdminForm, CommentForm, AskQuestionForm
from ..decorators import admin_required, permission_required
from .. import db
from ..models import Role, User, Post, Permission, Comment, Question

@main.after_app_request
def after_request(response):
	for query in get_debug_queries():
		if query.duration >= current_app.config['QA_SLOW_DB_QUERY_TIME']:
			current_app.logger.warning(
				'Slow query: %s\nParameters: %s\nDuration: %fs\nContext: %s\n' % (query.statement, query.parameters, query.duration, query.context))
	return response


@main.route('/', methods=['GET', 'POST'])
def index():
	form = PostForm()
	if current_user.can(Permission.WRITE_ARTICLES) and \
		form.validate_on_submit():
		post = Post(body=form.body.data,
					author=current_user._get_current_object())
		db.session.add(post)
		return redirect(url_for('.index'))
	page = request.args.get('page', 1, type=int)
	show_followed = False
	if current_user.is_authenticated:
		show_followed = bool(request.cookies.get('show_followed', ''))
	if show_followed:
		query = current_user.followed_posts
	else:
		query = Post.query
	pagination = query.order_by(Post.timestamp.desc()).paginate(
		page, per_page=current_app.config['ZHIHU_POSTS_PER_PAGE'],
		error_out=False)
	posts = pagination.items
	return render_template('index.html', form=form, posts=posts, show_followed=show_followed, pagination=pagination)

@main.route('/user/<username>')
def user(username):
	user = User.query.filter_by(username=username).first_or_404()
	page = request.args.get('page', 1, type=int)
	show_answer = False
	show_answer = bool(request.cookies.get('show_answer', ''))
	if show_answer:
		pagination = user.posts.order_by(Post.timestamp.desc()).paginate(page, per_page=current_app.config['ZHIHU_POSTS_PER_PAGE'], error_out=False)
		posts = pagination.items
		return render_template('user.html', user=user, posts=posts, pagination=pagination, show_answer=show_answer)
	else:
		pagination = user.questions.order_by(Question.timestamp.desc()).paginate(page, per_page=current_app.config['ZHIHU_POSTS_PER_PAGE'], error_out=False)
		questions = pagination.items
		return render_template('user.html', user=user, questions=questions, pagination=pagination, show_answer=show_answer)

@main.route('/edit-profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
	form = EditProfileForm()
	if form.validate_on_submit():
		current_user.name = form.name.data
		current_user.location = form.location.data
		current_user.about_me = form.about_me.data
		db.session.add(current_user)
		flash('Your profile has been updated.')
		return redirect(url_for('.user', username=current_user.username))
	form.name.data = current_user.name
	form.location.data = current_user.location
	form.about_me.data = current_user.about_me
	return render_template('edit_profile.html', form=form)

@main.route('/edit-profile/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_profile_admin(id):
	user = User.query.get_or_404(id)
	form = EditProfileAdminForm(user=user)
	if form.validate_on_submit():
		user.email = form.email.data
		user.username = form.username.data
		user.confirmed = form.confirmed.data
		user.role = Role.query.get(form.role.data)
		user.name = form.name.data
		user.location = form.location.data
		user.about_me = form.about_me.data
		db.session.add(user)
		flash('The profile has been updated.')
		return redirect(url_for('.user', username=user.username))
	form.email.data = user.email
	form.username.data = user.username
	form.confirmed.data = user.confirmed
	form.role.data = user.role_id
	form.name.data = user.name
	form.location.data = user.location
	form.about_me.data = user.about_me
	return render_template('edit_profile.html', form=form, user=user)

@main.route('/post/<int:id>', methods=['GET', 'POST'])
def post(id):
	post = Post.query.get_or_404(id)
	form = CommentForm()
	if form.validate_on_submit():
		comment = Comment(body=form.body.data,
				post=post, author=current_user._get_current_object())
		db.session.add(comment)
		flash('Your comment has been published.')
		return redirect(url_for('.post', id=post.id, page=-1))
	page = request.args.get('page', 1, type=int)
	if page == -1:
		page = (post.comments.count() - 1) / current_app.config['ZHIHU_COMMENTS_PER_PAGE'] + 1
	pagination = post.comments.order_by(Comment.timestamp.asc()).paginate(
		page, per_page=current_app.config['ZHIHU_COMMENTS_PER_PAGE'],
		error_out=False)
	comments = pagination.items
	return render_template('post.html', posts=[post], form=form,
				comments=comments, pagination=pagination)

@main.route('/edit-post/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
	post = Post.query.get_or_404(id)
	if current_user != post.author and \
			not current_user.can(Permission.ADMINISTER):
		abort(403)
	form = PostForm()
	if form.validate_on_submit():
		post.body = form.body.data
		db.session.add(post)
		flash('The post has been updated')
		return redirect(url_for('.post', id=post.id))
	form.body.data = post.body
	return render_template('edit_post.html', form=form)

@main.route('/follow/<username>')
@login_required
@permission_required(Permission.FOLLOW)
def follow(username):
	user = User.query.filter_by(username=username).first()
	if user is None:
		flash('Invalid user.')
		return redirect(url_for('.index'))
	if current_user.is_following(user):
		flash('You are already following this user.')
		return redirect(url_for('.user', username=username))
	current_user.follow(user)
	flash('You are now following %s.' % username)
	return redirect(url_for('.user', username=username))

@main.route('/unfollow/<username>')
@login_required
@permission_required(Permission.FOLLOW)
def unfollow(username):
	user = User.query.filter_by(username=username).first()
	if user is None:
		flash('Invalid user.')
		return redirect(url_for('.index'))
	if not current_user.is_following(user):
		flash('You are not following this user.')
		return redirect(url_for('.user', username=username))
	current_user.unfollow(user)
	flash('You are not following %s anymore.' % username)
	return redirect(url_for('.user', username=username))

@main.route('/followers/<username>')
def followers(username):
	user = User.query.filter_by(username=username).first()
	if user is None:
		flash('Invalid user.')
		return redirect(url_for('.index'))
	page = request.args.get('page', 1, type=int)
	pagination = user.followers.paginate(
		page, per_page=current_app.config['ZHIHU_FOLLOWERS_PER_PAGE'],
		error_out=False)
	follows = [{'user': item.follower, 'timestamp': item.timestamp}
				for item in pagination.items]
	return render_template('followers.html', user=user, title='Followers of', endpoint='.followers', pagination=pagination, follows=follows)

@main.route('/followed-by/<username>')
def followed_by(username):
	user = User.query.filter_by(username=username).first()
	if user is None:
		flash('Invalid user.')
		return redirect(url_for('.index'))
	page = request.args.get('page', 1, type=int)
	pagination = user.followed.paginate(
		page, per_page=current_app.config['ZHIHU_FOLLOWERS_PER_PAGE'],
		error_out=False)
	follows = [{'user': item.followed, 'timestamp': item.timestamp}
				for item in pagination.items]
	return render_template('followers.html', user=user, title='Followed by', endpoint='.followed_by', pagination=pagination, follows=follows)

@main.route('/all')
@login_required
def show_all():
	resp = make_response(redirect(url_for('.index')))
	resp.set_cookie('show_followed', '', max_age=30*24*60*60)
	return resp

@main.route('/followed')
@login_required
def show_followed():
	resp = make_response(redirect(url_for('.index')))
	resp.set_cookie('show_followed', '1', max_age=30*24*60*60)
	return resp

@main.route('/show-question/<username>')
def show_question(username):
	resp = make_response(redirect(url_for('.user', username=username)))
	resp.set_cookie('show_answer', '')
	return resp

@main.route('/show-answer/<username>')
def show_answer(username):
	resp = make_response(redirect(url_for('.user', username=username)))
	resp.set_cookie('show_answer', '1')
	return resp

@main.route('/moderate')
@login_required
@permission_required(Permission.MODERATE_COMMENTS)
def moderate():
	page = request.args.get('page', 1, type=int)
	pagination = Comment.query.order_by(Comment.timestamp.desc()).paginate(
		page, per_page=current_app.config['ZHIHU_COMMENTS_PER_PAGE'],
		error_out=False)
	comments = pagination.items
	return render_template('moderate.html', comments=comments, pagination=pagination, page=page)

@main.route('/moderate/enable/<int:id>')
@login_required
@permission_required(Permission.MODERATE_COMMENTS)
def moderate_enable(id):
	comment = Comment.query.get_or_404(id)
	comment.disabled = False
	db.session.add(comment)
	return redirect(url_for('.moderate', page=request.args.get('page', 1, type=int)))
	
@main.route('/moderate/disable/<int:id>')
@login_required
@permission_required(Permission.MODERATE_COMMENTS)
def moderate_disable(id):
	comment = Comment.query.get_or_404(id)
	comment.disabled = True
	db.session.add(comment)
	return redirect(url_for('.moderate', page=request.args.get('page', 1, type=int)))

@main.route('/questions', methods=['GET', 'POST'])
def questions():
	form = AskQuestionForm()
	if form.validate_on_submit():
		question = Question(title=form.title.data, body=form.body.data,
						author=current_user._get_current_object())
		db.session.add(question)
		flash('Your question has been published.')
		return redirect(url_for('.index'))
	page = request.args.get('page', 1, type=int)
	pagination = Question.query.order_by(Question.timestamp.desc()).paginate(page, per_page=current_app.config['ZHIHU_POSTS_PER_PAGE'], error_out=False)
	questions = pagination.items
	return render_template('ask_question.html', form=form, questions=questions, pagination=pagination)

@main.route('/question/<int:id>', methods=['GET', 'POST'])
def question(id):
	question = Question.query.get_or_404(id)
	form = PostForm()
	if form.validate_on_submit():
		post = Post(body=form.body.data,
					author=current_user._get_current_object(),
					question=question)
		db.session.add(post)
		flash('Your idea has been published.')
		return redirect(url_for('.question', id=question.id, page=-1))
	page = request.args.get('page', 1, type=int)
	if page == -1:
		page = (question.posts.count() - 1) // current_app.config['ZHIHU_POSTS_PER_PAGE'] + 1
	pagination = question.posts.order_by(Post.timestamp.asc()).paginate(
		page, per_page=current_app.config['ZHIHU_POSTS_PER_PAGE'],
		error_out=False)
	posts = pagination.items
	return render_template('question.html', question=question, form=form, posts=posts, pagination=pagination)

@main.route('/focus-post/<int:id>')
@login_required
def focus_post(id):
	post = Post.query.get_or_404(id)
	if current_user.is_focus_post(post):
		flash('You are already focusing this post.')
		return redirect(request.args.get('next') or url_for('.index'))
	current_user.focus_post(post)
	return redirect(request.args.get('next') or url_for('.index'))

@main.route('/unfocus-post/<int:id>')
@login_required
def unfocus_post(id):
	post = Post.query.get_or_404(id)
	if not current_user.is_focus_post(post):
		flash('You are not focusing this post.')
		return redirect(request.args.get('next') or url_for('.index'))
	current_user.unfocus_post(post)
	return redirect(request.args.get('next') or url_for('.index'))

@main.route('/focus-post-users/<int:id>')
def focus_post_users(id):
	post = Post.query.get_or_404(id)
	page = request.args.get('page', 1, type=int)
	pagination = post.focus_users.paginate(
		page, per_page=current_app.config['ZHIHU_FOLLOWERS_PER_PAGE'],
		error_out=False)
	users = pagination.items
	return render_template('focus_users.html', post=post, users=users, pagination=pagination)

@main.route('/focus-question/<int:id>')
@login_required
def focus_question(id):
	question = Question.query.get_or_404(id)
	if current_user.is_focus_question(question):
		flash('You are already focusing this question.')
		return redirect(url_for('.questions'))
	current_user.focus_question(question)
	return redirect(url_for('.questions'))

@main.route('/unfocus-question/<int:id>')
@login_required
def unfocus_question(id):
	question = Question.query.get_or_404(id)
	if not current_user.is_focus_question(question):
		flash('You are not focusing this question,')
		return redirect(url_for('.questions'))
	current_user.unfocus_question(question)
	return redirect(url_for('.questions'))

@main.route('/focus-question-users/<int:id>')
def focus_question_users(id):
	question = Question.query.get_or_404(id)
	page = request.args.get('page', 1, type=int)
	pagination = question.focus_users.paginate(
		page, per_page=current_app.config['ZHIHU_FOLLOWERS_PER_PAGE'],
		error_out=False)
	users = pagination.items
	return render_template('focus_question_users.html', question=question, users=users, pagination=pagination)

@main.route('/add-post/<int:id>')
@login_required
def add_post(id):
	question = Question.query.get_or_404(id)
	return redirect(url_for('.question', id=question.id))

@main.route('/head')
def head():
	return render_template('head.html')

