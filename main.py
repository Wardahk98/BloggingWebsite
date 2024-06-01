from datetime import date
from flask import Flask, abort, render_template, redirect, url_for, flash, request
from flask_bootstrap import Bootstrap5
from flask_ckeditor import CKEditor
from flask_gravatar import Gravatar
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user, login_required
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship, DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Text, ForeignKey
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
# Import your forms from the forms.py
from forms import CreatePostForm, RegisterUser, Login, Comment
from typing import List
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
Bootstrap5(app)

# Configure Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return db.get_or_404(User, user_id)


def admin_only(funct):
    @wraps(funct)
    def wrapper_function(*args, **kwargs):
        if current_user.id != 1:
            return abort(403)
        return funct(*args, **kwargs)

    return wrapper_function


# CREATE DATABASE
class Base(DeclarativeBase):
    pass


app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///posts.db'
db = SQLAlchemy(model_class=Base)
db.init_app(app)


# CONFIGURE TABLES
# Create a User table for all your registered users.
class User(UserMixin, db.Model):
    __tablename__ = "reg_user"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(250), unique=True)
    password: Mapped[str] = mapped_column(String(250), nullable=False)
    name: Mapped[str] = mapped_column(String(250), nullable=False)
    # ----------------------------------------------------------------
    # ----------------------- BlogPost Parent --------------------------
    post: Mapped[List["BlogPost"]] = relationship(back_populates="author")
    # ----------------------- CommentData Parent -----------------------
    user_comment: Mapped[List["CommentData"]] = relationship(back_populates="comment_author")


class BlogPost(db.Model):
    __tablename__ = "blog_posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    subtitle: Mapped[str] = mapped_column(String(250), nullable=False)
    date: Mapped[str] = mapped_column(String(250), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    img_url: Mapped[str] = mapped_column(String(250), nullable=False)
    # ----------------------- User Child -----------------------------------
    author_id: Mapped[int] = mapped_column(Integer, ForeignKey("reg_user.id"))
    author: Mapped["User"] = relationship(back_populates="post")
    # ----------------------- CommentData Parent ----------------------------
    comment_parent: Mapped[List["CommentData"]] = relationship(back_populates="post_comment")


class CommentData(db.Model):
    __tablename__ = "comments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    # ----------------------- User Child ------------------------------
    author_id: Mapped[int] = mapped_column(Integer, ForeignKey("reg_user.id"))
    comment_author: Mapped["User"] = relationship(back_populates="user_comment")
    # ----------------------- BlogPost Child ----------------------------
    post_comment_id: Mapped[int] = mapped_column(Integer, ForeignKey("blog_posts.id"))
    post_comment: Mapped["BlogPost"] = relationship(back_populates="comment_parent")


class ContactForm(db.Model):
    __tablename__ = "contact-form"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False)
    phone: Mapped[int] = mapped_column(Integer)
    message: Mapped[str] = mapped_column(Text, nullable=False)


with app.app_context():
    db.create_all()


# Use Werkzeug to hash the user's password when creating a new user.
@app.route('/register', methods=["POST", "GET"])
def register():
    reg_form = RegisterUser()
    if reg_form.validate_on_submit():
        email = reg_form.email.data
        password = reg_form.password.data
        name = reg_form.name.data
        print(f"{email} - {password} - {name}")
        hashed_password = generate_password_hash(password=password, method="pbkdf2", salt_length=8)
        print(hashed_password)
        print(f"the password checker: {check_password_hash(hashed_password, password)}")
        with app.app_context():
            data = db.session.execute(db.select(User).where(User.email == email)).scalar()
            if data is None:
                new_user = User(
                    email=email,
                    password=hashed_password,
                    name=name
                )
                db.session.add(new_user)
                db.session.commit()
                login_user(new_user)
                print(current_user.is_authenticated)
                return redirect(url_for("get_all_posts"))
            else:
                flash("User already registered")
                return redirect(url_for("login"))

    return render_template("register.html", form=reg_form, logged_out=current_user.is_authenticated)


# Retrieve a user from the database based on their email.
@app.route('/login', methods=["POST", "GET"])
def login():
    login_form = Login()
    if login_form.validate_on_submit():
        log_email = login_form.email.data
        log_password = login_form.password.data
        print(f"{log_email} - {log_password}")
        with app.app_context():
            data = db.session.execute(db.select(User).where(User.email == log_email)).scalar()
            if data is None:
                flash("User don't exist.")
                return redirect(url_for("register"))
            elif not check_password_hash(data.password, log_password):
                flash("Wrong credentials.")
                return redirect(url_for("login"))
            else:
                login_user(data)
                # print(data.email)
                # print(check_password_hash(data.password, log_password))
                print(f"authentiated:{current_user.is_authenticated}")

                return redirect(url_for("get_all_posts"))
    return render_template("login.html", form=login_form, logged_out=current_user.is_authenticated)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route('/')
def get_all_posts():
    result = db.session.execute(db.select(BlogPost))
    posts = result.scalars().all()
    # author_id = [x.author_id for x in posts]
    # author = []
    # for x in author_id:
    #     author_data = db.session.execute(db.select(User).where(User.id == x)).scalar()
    #     author.append(author_data.name)
    #     print(author)
    post = []
    for x in posts:
        a = {"id": x.id,
             "title": x.title,
             "subtitle": x.subtitle,
             "author": db.get_or_404(User, x.author_id).name,
             "date": x.date}
        post.append(a)
        print(post)
    # print(f"The post author id :{posts[0].author_id}")
    if current_user.is_authenticated:
        u_id = True
        print(f"home u_id: {u_id}-{current_user}")
    else:
        u_id = False
        print(f"home u_id: {u_id}-{current_user}")
    return render_template("index.html", all_posts=post, u_id=u_id,
                           logged_out=current_user.is_authenticated)


# Allow logged-in users to comment on posts
@app.route("/post/<int:post_id>", methods=["GET", "POST"])
def show_post(post_id):
    requested_post = db.get_or_404(BlogPost, post_id)
    print(requested_post)
    author = db.get_or_404(User, requested_post.author_id).name
    comment_form = 0
    if current_user.is_authenticated:
        comment_form = Comment()
        if comment_form.validate_on_submit():
            clean_text = comment_form.comment.raw_data[0].replace("<p>", "")
            clean_text2 = clean_text.replace("</p>\r\n", "")
            print(comment_form.comment.data)
            print(clean_text2)
            comment_data = CommentData(
                text=clean_text2,
                author_id=current_user.id,
                post_comment_id=post_id
            )
            db.session.add(comment_data)
            db.session.commit()
            print("Comment added")
        if current_user.id == 1 or author == current_user.name:
            u_id = True
            print(f"show post u_id: {u_id}- {current_user}")
        else:
            u_id = False
            print(f"show post u_id: {u_id}- {current_user}")
    else:
        u_id = False
    comment_data = []
    with app.app_context():
        data = db.session.execute(db.select(CommentData).where(CommentData.post_comment_id == post_id)).scalars()
        for x in data:
            print(x.author_id)
            # comments_author.append(db.get_or_404(User, x.author_id).name)
            a = {"author": db.get_or_404(User, x.author_id).name,
                 "comment": x.text,
                 "email": db.get_or_404(User, x.author_id).email}
            comment_data.append(a)
            print(comment_data)
    gravatar = Gravatar(app,
                        size=100,
                        rating='g',
                        default='retro',
                        force_default=False,
                        force_lower=False,
                        use_ssl=False,
                        base_url=None)
    return render_template("post.html", post=requested_post, author=author, u_id=u_id,
                           comment_form=comment_form, comments_data=comment_data,
                           logged_out=current_user.is_authenticated,
                           gravatar=gravatar)


# Use a decorator so only an admin user can create a new post
@app.route("/new-post", methods=["GET", "POST"])
@login_required
@admin_only
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form, logged_out=current_user.is_authenticated)


# Use a decorator so only an admin user can edit a post
@app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])
@admin_only
@login_required
def edit_post(post_id):
    post = db.get_or_404(BlogPost, post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.author = current_user
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))
    return render_template("make-post.html", form=edit_form, is_edit=True, logged_out=current_user.is_authenticated)


# Use a decorator so only an admin user can delete a post
@app.route("/delete/<int:post_id>")
@login_required
@admin_only
def delete_post(post_id):
    post_to_delete = db.get_or_404(BlogPost, post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


@app.route("/about")
def about():
    return render_template("about.html", logged_out=current_user.is_authenticated)


@app.route("/contact", methods=["POST", "GET"])
def contact():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        phone = request.form.get("phone")
        msg = request.form.get("message")
        contact_form = ContactForm(
            name=name,
            email=email,
            phone=phone,
            message=msg,
        )
        db.session.add(contact_form)
        db.session.commit()
        flash("Your message is delivered. We will get to you soon.")
    return render_template("contact.html", logged_out=current_user.is_authenticated)


if __name__ == "__main__":
    app.run(debug=True, port=5002)
