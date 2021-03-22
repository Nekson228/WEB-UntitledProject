from flask import Flask, render_template, redirect, url_for
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename

from data.forms import *
from data.db_session import create_session, global_init
from data.__all_models import *

import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'yandexlyceum_secret_key'

login_manager = LoginManager()
login_manager.init_app(app)


@app.route('/', methods=['GET', 'POST'])
def index():
    if current_user.is_authenticated:
        form = SearchForm()
        if form.validate_on_submit():
            session = create_session()
            user = session.query(User).filter(User.phone_number == form.number_field.data).first()
            if not user:
                return render_template('index.html', form=form, message='Пользователь не найден')
            return render_template('index.html', form=form, user=user)
        return render_template('index.html', form=form)
    return render_template('index.html')


@login_manager.user_loader
def load_user(user_id):
    session = create_session()
    return session.query(User).get(user_id)


@app.route('/register', methods=["POST", "GET"])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        session = create_session()
        user = User()
        user.name = form.name_field.data
        user.surname = form.surname_field.data
        user.birthday = form.birthday_field.data
        user.email = form.email_field.data
        user.phone_number = form.phone_number_field.data
        user.set_password(form.password_field.data)
        session.add(user)
        session.commit()
        return redirect('/')
    return render_template('registration.html', form=form)


@app.route('/login', methods=["POST", "GET"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        session = create_session()
        user = session.query(User).filter(User.email == form.email_field.data).first()
        if user and user.check_password(form.password_field.data):
            login_user(user, remember=form.remember_me.data)
            return redirect('/')
        return render_template('login.html', message="Неправильный логин или пароль", form=form)
    return render_template('login.html', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/')


@app.route('/conversation/<int:user_id>', methods=['POST', 'GET'])
@login_required
def conversation(user_id):
    form = MessageForm()
    session = create_session()
    messages = session.query(Message).filter(((Message.to_id == current_user.id) & (Message.from_id == user_id)) |
                                             ((Message.from_id == current_user.id) & (Message.to_id == user_id)))
    companion = session.query(User).filter(User.id == user_id).first()
    if form.validate_on_submit():
        msg, cnt = Message(), Content()
        cnt.content = form.message_field.data
        session.add(cnt)
        session.commit()
        msg.to_id = user_id
        msg.from_id = current_user.id
        msg.content_id = cnt.id
        session.add(msg)
        session.commit()
        return redirect(f"/conversation/{user_id}")
    return render_template('chat.html', form=form, messages=messages, companion=companion)


@app.route('/profile/<int:user_id>')
@login_required
def show_profile(user_id):
    session = create_session()
    user = session.query(User).filter(User.id == user_id).first()
    pic = session.query(Avatar).filter(Avatar.refers_to == user_id).first()
    if pic:
        profile_pic = url_for('static', filename=f"avatars/{pic.link}")
    else:
        profile_pic = url_for('static', filename='avatars/anon.png')
    return render_template('profile.html', user=user, pic=profile_pic)


@app.route('/profile/avatar/<int:user_id>', methods=['GET', 'POST'])
@login_required
def change_avatar(user_id):
    form = AvatarForm()
    session = create_session()
    if form.validate_on_submit():
        photo = form.link_field.data
        file = secure_filename(photo.filename)
        avatars = session.query(Avatar).filter(Avatar.refers_to == user_id).first()
        if avatars:
            os.remove(os.path.join(app.root_path, 'static', 'avatars', avatars.link))
            avatars.link = file
            photo.save(os.path.join(app.root_path, 'static', 'avatars', file))
            session.commit()
        else:
            avatar = Avatar()
            avatar.refers_to = user_id
            avatar.link = file
            photo.save(os.path.join(app.root_path, 'static', 'avatars', file))
            session.add(avatar)
            session.commit()
        return redirect(f'/profile/{user_id}')
    return render_template('avatar.html', form=form)


if __name__ == '__main__':
    global_init('db/chats_db.sqlite')
    app.run('127.0.0.1', 8080, debug=True)
