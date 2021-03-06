from flask import Flask, render_template, request, redirect, jsonify
from flask import url_for, flash
from sqlalchemy import create_engine, asc, desc
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Category, Item, User
from flask import session as login_session
import random
import string
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests

app = Flask(__name__)

CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Category and Item Application"


# Connect to Database and create database session
engine = create_engine('sqlite:///itemcatalog.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


@app.route('/login')
def showLogin():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    # return "The current session state is %s" % login_session['state']
    return render_template('login.html', STATE=state)

'''
Uses Google APIs to handle user authentication.
'''


@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(
            json.dumps('Current user is already connected.'),
            200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']

    # Create user if doesn't exist
    user_id = getUserID(login_session['email'])
    if not user_id:
        createUser(login_session)
        login_session['user_id'] = user_id
    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;'
    output += '-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
    flash("you are now logged in as %s" % login_session['username'])
    print "done!"
    return output


@app.route('/gdisconnect')
def gdisconnect():
    access_token = login_session['access_token']
    print 'In gdisconnect access token is %s', access_token
    print 'User name is: '
    print login_session['username']
    if access_token is None:
        print 'Access Token is None'
        response = make_response(json.dumps('Current user not connected.'),
                                 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    token = login_session['access_token']
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    print 'result is '
    print result
    print 'try again '
    print result['status']
    if result['status'] == '200' or result['status'] == '400':
        del login_session['access_token']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    else:

        response = make_response(
            json.dumps('Failed to revoke token for given user.',
                       400))
        response.headers['Content-Type'] = 'application/json'
        return response

'''
This will show all categories, with all items nested in the
appropriate category
'''


@app.route('/catalog.JSON')
def categorysJSON():
    categories = session.query(Category).order_by(asc(Category.name))
    serializedCategories = []
    for i in categories:
        new_cat = i.serialize
        items = session.query(Item).filter_by(category_name=i.name).all()
        serializedItems = []
        for j in items:
            serializedItems.append(j.serialize)
        new_cat['items'] = serializedItems
        serializedCategories.append(new_cat)
    return jsonify(categories=[serializedCategories])


@app.route('/', methods=['GET', 'POST'])
@app.route('/catalog/', methods=['GET', 'POST'])
def showCategorys():
    categorys = session.query(Category).order_by(asc(Category.name))
    items = session.query(Item).order_by(Item.mydate.desc()).limit(10)
    if 'username' not in login_session:
        return render_template('publiccategorys.html',
                               categorys=categorys, items=items)
    else:
        return render_template('categorys.html', categorys=categorys,
                               items=items)


@app.route('/catalog/<string:categoryname>/items/', methods=['GET', 'POST'])
def showItemList(categoryname):

    category = session.query(Category).filter_by(name=categoryname).one()
    categories = session.query(Category).all()

    items = session.query(Item).filter_by(
        category_name=category.name).all()
    if 'username' not in login_session:
        return render_template('publicShowCategoryItems.html',
                               categories=categories, items=items,
                               category=category)
    else:
        creator = getUserInfo(login_session['username'])
        if creator.name != login_session['username']:
            return render_template('publicShowCategoryItems.html',
                                   categories=categories, items=items,
                                   category=category)
        else:
            return render_template('showCategoryItems.html',
                                   categories=categories, items=items,
                                   category=category, creator=creator)


@app.route('/catalog/<string:categoryname>/<string:itemname>/',
           methods=['GET', 'POST'])
def showItem(categoryname, itemname):

    item = session.query(Item).filter_by(name=itemname).one()
    try:
        username = login_session['username']
        print "showItem: was username in login session? %s" % username

        creator = getUserInfo(username)

    except:
        print "showItem hit exception trying to get user info"
        return render_template('publicitem.html', item=item)

    not_in_session = 'username' not in login_session
    if not_in_session or creator is None or creator.name != username:
        if creator is None:
            print "showItem creator was None"
        if creator.name != username:
            print "creator.name=%s" % creator.name
        return render_template('publicitem.html', item=item)
    else:
        return render_template('item.html', item=item,  creator=creator)

'''
Allows a logged in user to create a new item.
'''


@app.route('/catalog/new/', methods=['GET', 'POST'])
def newItem():
    print "enter newItem()"
    if 'username' not in login_session:
        print "username not in session, logout"
        return redirect('/login')

    categories = session.query(Category).all()

    if request.method == 'POST':
        user = getUserInfo(login_session['username'])
        category = session.query(Category).filter_by(
            name=request.form['category']).one()
        newItem = Item(name=request.form['name'],
                       description=request.form['description'],
                       price=request.form['price'], category=category,
                       user_id=user.id)
        session.add(newItem)
        session.commit()
        flash('Item Successfully Added')
        return redirect(url_for('showCategorys'))
    else:
        print "method is GET"
        return render_template('newItem.html', categories=categories)

'''
Edits an item.  If the user wants to edit an item they have to
be logged in.  Not only that, they have to be the creator of
the item, or they will receive an error message and the item
will not be edited
'''


@app.route('/catalog/<string:itemname>/edit', methods=['GET', 'POST'])
def editItem(itemname):
    if 'username' not in login_session:
        return redirect('/login')

    editedItem = session.query(Item).filter_by(name=itemname).one()
    categories = session.query(Category).all()
    oUser = session.query(User).filter_by(id=editedItem.user_id).one()
    category = session.query(Category).filter_by(
        name=editedItem.category_name).one()
    if request.method == 'POST':
        if oUser.name != login_session['username']:
            flash('You can only edit items which you created')
            return redirect(url_for('showCategorys'))
        oName = editedItem.name
        oDesc = editedItem.description
        oPrice = editedItem.price
        oCat = editedItem.category_name

        if request.form['name']:
            editedItem.name = request.form['name']
        if request.form['description']:
            editedItem.description = request.form['description']
        if request.form['price']:
            editedItem.price = request.form['price']
        if request.form['category']:
            editedItem.category_name = request.form['category']
        name = editedItem.name
        desc = editedItem.description
        price = editedItem.price
        cat = editedItem.category_name
        if (oName != name or oDesc != desc or oPrice != price or oCat != cat):
            session.add(editedItem)
            session.commit()
            flash('Item Successfully Edited')

        return redirect(url_for('showCategorys'))
    else:
        return render_template('editItem.html', item=editedItem,
                               categories=categories)

'''
Deletes an item.  If the user wants to delete item they have to
be logged in.  Not only that, they have to be the creator of
the item, or they will receive an error message and the item
will not be deleted.
'''


@app.route('/catalog/<string:itemname>/delete', methods=['GET', 'POST'])
def deleteItem(itemname):
    if 'username' not in login_session:
        return redirect('/login')

    itemToDelete = session.query(Item).filter_by(name=itemname).one()
    oUser = session.query(User).filter_by(id=itemToDelete.user_id).one()
    if request.method == 'POST':
        if oUser.name != login_session['username']:
            flash('You can only delete items which you created')
            return redirect(url_for('showCategorys'))
        session.delete(itemToDelete)
        session.commit()
        flash('Item Successfully Deleted')
        return redirect(url_for('showCategorys'))
    else:
        return render_template('deleteItem.html', itemname=itemToDelete.name)


def getUserID(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        print "getUserID exception thrown"
        return None


def getUserInfo(username):
    try:
        user = session.query(User).filter_by(name=username).one()
        return user
    except:
        print "getUserInfo exception thrown"
        return None


def createUser(login_session):
    newUser = User(name=login_session['username'],
                   email=login_session['email'],
                   picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    print "user created! %s" % user.name
    return user.id

if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=8000)
