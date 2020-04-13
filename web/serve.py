from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date, timedelta
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
from web import app, db, login_manager
from .models import User, Habit, Log

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'GET':
        return render_template('signup.html')
    elif request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if username == '':
            flash('Please insert a username.')
            return redirect(url_for('signup'))

        if password == '':
            flash('Please insert a password.')
            return redirect(url_for('signup'))


        user = User.query.filter_by(username=username).first() # check if a user exists

        if user: # if a user is found, try again
            flash('Username already exists')
            return redirect(url_for('signup'))

        # create new user with the form data
        new_user = User(username=username, password=generate_password_hash(password, method='sha256'))

        # add the new user to the database
        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for('login'))

@app.route('/')
def home():
    return redirect(url_for('dashboard', current_date=date.today()))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')
    elif request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False

        user = User.query.filter_by(username=username).first()

        # check if user actually exists
        if not user:
            flash('This username does not exist')
            return redirect(url_for('login'))
        if not check_password_hash(user.password, password):
            flash('Incorrect password')
            return redirect(url_for('login'))

        # if the username exists and the password was correct, go to the user's "dashboard"
        login_user(user, remember=remember)
        return redirect(url_for('dashboard', current_date=date.today()))

@app.route('/dashboard/<current_date>', methods=['GET', 'POST'])
@login_required
def dashboard(current_date):
    if request.method == 'GET':
        '''
        Logic to find the logs that should be displayed on the dashboard for the given day.

        This should:
            1. Find all current active habits created on today or earlier. These are all the habits that should have logs on the current day.
            2. Find all the logs for the found habits.
            3.

        '''

        habits = Habit.query.filter_by(user_id=current_user.id, active=True).filter(Habit.date_created <= datetime.strptime(current_date, '%Y-%m-%d')).all()

        if habits:
            for habit in habits:
                log = Log.query.filter_by(habit_id=habit.id, date=datetime.strptime(current_date, '%Y-%m-%d')).all()
                if not log:
                    log_ = Log(
                        user_id=current_user.id,
                        habit_id=habit.id,
                        date=datetime.strptime(current_date, '%Y-%m-%d')
                    )
                    db.session.add(log_)
                    db.session.commit()

        habit_log_iter = db.session.query(Habit, Log).filter(Habit.id == Log.habit_id, Log.date == datetime.strptime(current_date, '%Y-%m-%d'), Habit.active == True).all()

        #how many habits were completed, how many habits were not
        count = {
            'completed' : len(db.session.query(Log).filter(Log.date == datetime.strptime(current_date, '%Y-%m-%d'), Log.status==True).all()),
            'todo' : len(db.session.query(Log).filter(Log.date == datetime.strptime(current_date, '%Y-%m-%d'), Log.status==False).all()),
            'total' : len(db.session.query(Log).filter(Log.date == datetime.strptime(current_date, '%Y-%m-%d')).all())
        }

        return render_template('dashboard.html', user=current_user, date=current_date, habits=habit_log_iter, count=count)

    if request.method == 'POST':
        current_date = datetime.strptime(current_date, '%Y-%m-%d')
        if request.form.get('increment') == 'yesterday':
            current_date = current_date - timedelta(days=1)
        elif request.form.get('increment') == 'tomorrow':
            current_date = current_date + timedelta(days=1)
        elif request.form.get('increment') == 'today':
            current_date = current_date.today()

        elif request.form.get('done'):
            for checked_off_id in request.form.getlist('done'):
                log = Log.query.filter_by(user_id=current_user.id, id=checked_off_id, date=current_date).first()
                log.status = True
                db.session.add(log)
                db.session.commit()

        elif request.form.get('undo-done'):
            for checked_off_id in request.form.getlist('undo-done'):
                log = Log.query.filter_by(user_id=current_user.id, id=checked_off_id).filter(Log.date.like(current_date)).first()
                log.status = False
                db.session.add(log)
                db.session.commit()

        return redirect(url_for('dashboard', current_date=datetime.strftime(current_date, '%Y-%m-%d')))

@app.route('/add_habit', methods=['GET', 'POST'])
@login_required
def add_habit():
    if request.method == 'GET':
        return render_template('add_habit.html', user=current_user)
    elif request.method == 'POST':
        habit = Habit(
            user_id=current_user.id,
            title=request.form.get('title'),
            description=request.form.get('description'),
            frequency=request.form.get('frequency'),
            date_created=datetime.today(),
            active=True
        )

        db.session.add(habit)
        db.session.flush()

        log = Log(
            user_id=current_user.id,
            habit_id=habit.id,
            date=date.today()
        )

        db.session.add(log)

        db.session.commit()
        return redirect(url_for('dashboard', current_date=date.today()))

@app.route('/habit/<habit_id>')
@login_required
def habit(habit_id):
    habit = Habit.query.filter_by(id=habit_id, user_id=current_user.id).first()
    return render_template('habit.html', habit=habit)

@app.route('/habit/<habit_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_habit(habit_id):
    habit = Habit.query.filter_by(id=habit_id, user_id=current_user.id).first()
    if request.method == 'GET':
        return render_template('edit_habit.html', habit=habit)
    elif request.method == 'POST':
        if request.form.get('title') or request.form.get('description') or request.form.get('frequency'):
            habit.title = request.form.get('title')
            habit.description = request.form.get('description')
            habit.frequency = request.form.get('frequency')

            db.session.add(habit)
            db.session.commit()

            return redirect(url_for('habit', habit_id=habit.id))

        elif request.form.get('archive'):
            habit.active = False

            db.session.add(habit)
            db.session.commit()

            return redirect(url_for('habit', habit_id=habit.id))

        elif request.form.get('unarchive'):
            habit.active = True

            db.session.add(habit)
            db.session.commit()

            return redirect(url_for('habit', habit_id=habit.id))

        elif request.form.get('delete'):
            Log.query.filter_by(habit_id=habit.id).delete()

            db.session.delete(habit)
            db.session.commit()

            return redirect(url_for('dashboard', current_date=date.today()))

@app.route('/archive')
@login_required
def archive():
    habits = Habit.query.filter_by(user_id=current_user.id, active=False).all()
    print(habits)
    return render_template("archive.html", habits=habits)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run()
