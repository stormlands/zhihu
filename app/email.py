from threading import Thread
from flask import current_app, render_template
from flask_mail import Message
from . import mail

def send_async_email(app, msg):
	with app.app_context():
		mail.send(msg)

def send_email():
	pass

