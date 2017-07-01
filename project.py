from flask import Flask, render_template, request, redirect, jsonify, url_for, flash
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


# Create anti-forgery state token
@app.route('/login')
def showLogin():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    # return "The current session state is %s" % login_session['state']
    return render_template('login.html', STATE=state)


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
        response = make_response(json.dumps('Current user is already connected.'),
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
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
    flash("you are now logged in as %s" % login_session['username'])
    print "done!"
    return output

# DISCONNECT - Revoke a current user's token and reset their login_session


@app.route('/gdisconnect')
def gdisconnect():
    access_token = login_session['access_token']
    print 'In gdisconnect access token is %s', access_token
    print 'User name is: ' 
    print login_session['username']
    if access_token is None:
 	print 'Access Token is None'
    	response = make_response(json.dumps('Current user not connected.'), 401)
    	response.headers['Content-Type'] = 'application/json'
    	return response
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % login_session['access_token']
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    print 'result is '
    print result
    print 'try again '
    print result['status']
    # If the token is expired it can't be revoked.  For now assume all 400s mean that the token is expired
    if result['status'] == '200'  or result['status'] == '400':
	del login_session['access_token'] 
    	del login_session['gplus_id']
    	del login_session['username']
    	del login_session['email']
    	del login_session['picture']
    	response = make_response(json.dumps('Successfully disconnected.'), 200)
    	response.headers['Content-Type'] = 'application/json'
    	return response
    else:
	
    	response = make_response(json.dumps('Failed to revoke token for given user.', 400))
    	response.headers['Content-Type'] = 'application/json'
    	return response


# JSON APIs to view Category Information
@app.route('/catalog/<int:category_id>/itemlist/JSON')
def categoryItemListJSON(category_id):
    category = session.query(Category).filter_by(id=category_id).one()
    items = session.query(Item).filter_by(
        category_id=category_id).all()
    return jsonify(Items=[i.serialize for i in items])


@app.route('/catalog/<int:category_id>/itemlist/<int:item_id>/JSON')
def itemJSON(category_id, item_id):
    Item = session.query(Item).filter_by(id=item_id).one()
    return jsonify(Item=Item.serialize)


@app.route('/catalog/JSON')
def categorysJSON():
    categorys = session.query(Category).all()
    return jsonify(categorys=[r.serialize for r in categorys])


# Show all categorys
@app.route('/', methods=['GET', 'POST'])
@app.route('/catalog/', methods=['GET', 'POST'])
def showCategorys():
    categorys = session.query(Category).order_by(asc(Category.name))
    items = session.query(Item).order_by(Item.mydate.desc()).limit(10)
    if 'username' not in login_session:
        return render_template('publiccategorys.html', categorys=categorys, items=items)
    else:
        return render_template('categorys.html', categorys=categorys, items=items)
    
# Create a new category


#@app.route('/catalog/category/new/', methods=['GET', 'POST'])
def newCategory():
    if 'username' not in login_session:
        return redirect('/login')

    if request.method == 'POST':
        newCategory = Category(name=request.form['name'], user_id = login_session['user_id'])
        session.add(newCategory)
        flash('New Category %s Successfully Created' % newCategory.name)
        session.commit()
        return redirect(url_for('showCategorys'))
    else:
        return render_template('newCategory.html')

# Edit a category


@app.route('/catalog/<int:category_id>/edit/', methods=['GET', 'POST'])
def editCategory(category_id):
    if 'username' not in login_session:
        return redirect('/login')

    editedCategory = session.query(
        Category).filter_by(id=category_id).one()
    if editedCategory.user_id != login_session['user_id']:
        return "<script>function myFunction() {alert('You are not authorized to edit this category.  Please create your own category in order to edit.');}</script><body onload='myFunction()''>"
    
    if request.method == 'POST':
        if request.form['name']:
            editedCategory.name = request.form['name']
            flash('Category Successfully Edited %s' % editedCategory.name)
            return redirect(url_for('showCategorys'))
    else:
        return render_template('editCategory.html', category=editedCategory)


# Delete a category
@app.route('/catalog/<int:category_id>/delete/', methods=['GET', 'POST'])
def deleteCategory(category_id):
    if 'username' not in login_session:
        return redirect('/login')
    categoryToDelete = session.query(
        Category).filter_by(id=category_id).one()
    if categoryToDelete.user_id != login_session['user_id']:
        return "<script>function myFunction() {alert('You are not authorized to delete this category.  Please create your own category in order to delete.');}</script><body onload='myFunction()''>"

    if request.method == 'POST':
        session.delete(categoryToDelete)
        flash('%s Successfully Deleted' % categoryToDelete.name)
        session.commit()
        return redirect(url_for('showCategorys', category_id=category_id))
    else:
        return render_template('deleteCategory.html', category=categoryToDelete)

# Show a category item list


@app.route('/catalog/<string:categoryname>/items/', methods=['GET', 'POST'])
def showItemList(categoryname):
   
    category = session.query(Category).filter_by(name=categoryname).one()
    categories = session.query(Category).all()
    
    items = session.query(Item).filter_by(
        category_name=category.name).all()
    if 'username' not in login_session  or creator is None or creator.name != login_session['username']:
        return render_template('publicitemlist.html', categories = categories, items=items, category=category)
    else:
        creator = getUserInfo(login_session['username'])
   
        return render_template('itemlist.html', categories = categories, items=items, category=category, creator=creator)

@app.route('/catalog/<string:categoryname>/<string:itemname>/', methods=['GET', 'POST'])
def showItem(categoryname, itemname):
   
    item = session.query(Item).filter_by(name=itemname).one()
    try:
        username = login_session['username']
        print "showItem: was username in login session? %s" % username
        
        creator = getUserInfo(username)
    
    except:
        print "showItem hit exception trying to get user info"
        return render_template('publicitem.html', item=item)
        
    if 'username' not in login_session  or creator is None or creator.name != username:
        if creator is None:
            print "showItem creator was None"
        if creator.name != username:
            print "creator.name=%s" % creator.name
        return render_template('publicitem.html', item=item)
    else:
        return render_template('item.html', item=item,  creator=creator)
        

# Create a new item
@app.route('/catalog/new/', methods=['GET', 'POST'])
def newItem():
    print "enter newItem()"
    if 'username' not in login_session:
        print "username not in session, logout"
        return redirect('/login')

    categories = session.query(Category).all()
    
    if request.method == 'POST':
        
    
        category = session.query(Category).filter_by(name=request.form['category']).one()
        
        newItem = Item( name=request.form['name'], 
            description=request.form['description'], price=request.form['price'], category = category)
       
        session.add(newItem)
        session.commit()
        flash('Item Successfully Added')
        return redirect(url_for('showCategorys'))
    else:
        print "method is GET"
        return render_template('newItem.html', categories = categories)


# Edit an item


@app.route('/catalog/<string:itemname>/edit', methods=['GET', 'POST'])
def editItem(itemname):
    if 'username' not in login_session:
        return redirect('/login')

    editedItem = session.query(Item).filter_by(name=itemname).one()
    
    category = session.query(Category).filter_by(id=category_id).one()
    if request.method == 'POST':
        if request.form['name']:
            editedItem.name = request.form['name']
        if request.form['description']:
            editedItem.description = request.form['description']
        if request.form['price']:
            editedItem.price = request.form['price']
        if request.form['catgory']:
            editedItem.category = request.form['category']
    
        session.add(editedItem)
        session.commit()
        flash('Item Successfully Edited')
        return redirect(url_for('showCategorys()'))
    else:
        return render_template('editItem.html', itemname=editedItem.name)


# Delete an item
@app.route('/catalog/<string:itemname>/delete', methods=['GET', 'POST'])
def deleteItem(itemname):
    if 'username' not in login_session:
        return redirect('/login')
    
    itemToDelete = session.query(Item).filter_by(id=item_id).one()
    
    if request.method == 'POST':
        session.delete(itemToDelete)
        session.commit()
        flash('Item Successfully Deleted')
        return redirect(url_for('showCategorys()'))
    else:
        return render_template('deleteItem.html', itemname=itemToDelete.name)

def getUserID(email):
    try:
        user = session.query(User).filter_by(email = email).one()
        print "getUserID got user %s" % user.name
        return user.id
    except:
        print "getUserID exception thrown"
        return None
        
def getUserInfo(username):
    try:
        print "getUserInfo username=%s" % username
        user = session.query(User).filter_by(name = username).one()
        return user
    except:
        print "getUserInfo exception thrown"
        return None
    
def createUser(login_session):
   newUser = User(name = login_session['username'], email = login_session['email'], picture = login_session['picture'])
   session.add(newUser)
   session.commit()
   user = session.query(User).filter_by(email = login_session['email']).one()
   print "user created! %s" % user.name
   return user.id

if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=8000)