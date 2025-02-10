from flask import Blueprint, render_template

main = Blueprint('main', __name__)

@main.route('/')
def index():
    return render_template('home.html')

@main.route('/home')
def home():
    return render_template('home.html', active_page='home')

@main.route('/event/find')
def findEvent():
    return render_template('findEvent.html') 
 
@main.route('/event/create')
def createEvent():
    return render_template('findEvent.html') 
 
@main.route('/event/organizer')
def contactOrganizer():
    return render_template('findEvent.html') 
 
@main.route('/help-center')
def helpCenter():
    return render_template('findEvent.html')
 
@main.route('/event/tickets')
def findMyTickets():
    return render_template('findEvent.html')

 