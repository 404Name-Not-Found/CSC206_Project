from flask import Flask, render_template, render_template_string, request, redirect, url_for, flash, session
from datetime import timedelta
from database import MyDatabase
from sql import cars
from dotenv import load_dotenv
from decimal import Decimal

load_dotenv()

app = Flask(__name__, static_url_path='/static', template_folder='templates')

db = MyDatabase(app)


# Function that returns all the SQL queries
def sql_queries():

    vSQL = cars.vehicleSQL()

    # To loop through sql queries:
    # https://stackoverflow.com/questions/16947276/flask-sqlalchemy-iterate-column-values-on-a-single-row
    queries = {
        'all_vehicles': vSQL.display_vehicles(),
        'vehicles': vSQL.all_vehicles(),
        'manufacturer': vSQL.vehicle_names(),
        'vehicle_types': vSQL.vehicle_type(),
        'vehicle_years': vSQL.vehicle_years(),
        'fuel_types': vSQL.vehicle_fuel_type(),
        'colors': vSQL.colors(),
        'users': vSQL.users(),
    }

    # Dictionary for car queries
    all_cars = {}

    # Loop through queries dictionary and match the data key to the sql value
    for key, sql in queries.items():
        all_cars[key] = db.query(sql)

    # Return the dictionary
    return all_cars


@app.route('/')
@app.route('/home')
def home():

    # Filter help from my boi ezi as well

    # First get the information related to the key from the URL
    manID = request.args.get('manufacturer_name')
    vehicletypeID = request.args.get('vehicle_type')
    modelyear = request.args.get('model_year')
    fueltype = request.args.get('fuel_type')
    colorid = request.args.get('color_selection')

    # Dictionary for the filters
    filters = {}

    # Add the information to the dictionary if it exists
    try:
        if manID:
            filters['manID'] = int(manID)
    except ValueError:
        pass
    try:
        if vehicletypeID:
            filters['vehicletypeID'] = int(vehicletypeID)
    except ValueError:
        pass
    try:
        if modelyear:
            filters['model_year'] = int(modelyear)
    except ValueError:
        pass
    if fueltype:
        filters['fueltype'] = fueltype
    try:
        if colorid:
            filters['colorid'] = int(colorid)
    except ValueError:
        pass

    qSQL = cars.vehicleSQL()

    car_query = sql_queries()

    # Calls the (scary) sellable vehicles query and passes the filters dictionary as the parameter
    output = db.query(qSQL.sellable_vehicles(filters if filters else None))

    return render_template('display.html', cars=car_query, vehicles=output, include_filters=True, display_color=True)

# Route for the vehicle details, takes a dynamic paramter for the sql query
@app.route('/vehicle/<vehicle_id>')
def vehicle_details(vehicle_id):

    qSQL = cars.vehicleSQL()
    car_query = qSQL.vehicle_details(vehicle_id)
    output = db.query(car_query)

    # Get the first item in the dictionary which is only 1 car long but anyways then display it on the details template
    car = output[0]

    
    # Get parts for the vehicle, excepct some don't have parts so handle that
    try:
        vid = int(vehicle_id)
    except (TypeError, ValueError):
        vid = None

    # Dictionary for car parts
    parts = []
    
    # If there is a vechile id
    if vid is not None:
        parts_sql = qSQL.parts_for_vehicle(vid)
        parts = db.query(parts_sql)


    seller = None
    buyer = None
    if vid is not None:

        # Get cusomter information
        tc_sql = qSQL.transaction_customers(vid)
        tc_res = db.query(tc_sql)

        # If database returne result
        if tc_res and len(tc_res) > 0:

            # Take the first row(Should only be 1)
            row = tc_res[0]

            # Populater seller then buyer with the correct information
            if row.get('seller_customerID') is not None:
                seller = {
                    'first_name': row.get('seller_first_name'),
                    'last_name': row.get('seller_last_name'),
                    'street': row.get('seller_street'),
                    'city': row.get('seller_city'),
                    'state': row.get('seller_state'),
                    'postal_code': row.get('seller_postal_code'),
                    'phone_number': row.get('seller_phone_number'),
                    'email_address': row.get('seller_email_address')
                }
            if row.get('buyer_customerID') is not None:
                buyer = {
                    'first_name': row.get('buyer_first_name'),
                    'last_name': row.get('buyer_last_name'),
                    'street': row.get('buyer_street'),
                    'city': row.get('buyer_city'),
                    'state': row.get('buyer_state'),
                    'postal_code': row.get('buyer_postal_code'),
                    'phone_number': row.get('buyer_phone_number'),
                    'email_address': row.get('buyer_email_address')
                }

    return render_template('details.html', car=car, parts=parts, seller=seller, buyer=buyer)

# Route to display all vehicles
@app.route('/all_vehicles')
def all_vehicles():
    
    qSQL = cars.vehicleSQL()
    output = db.query(qSQL.display_vehicles())

    car_query = sql_queries()

    return render_template('all_vehicles.html', vehicles=output, cars=car_query, include_filters=True, display_color=True)



# 3 Routes below for the various reports
@app.route('/sales')
def sales():

    qSQL = cars.vehicleSQL()
    output = db.query(qSQL.sale())

    return render_template('reports.html', info=output)


@app.route('/seller')
def seller():

    qSQL = cars.vehicleSQL()
    output = db.query(qSQL.seller())

    return render_template('seller.html', info=output)


@app.route('/statistics')
def stats():

    qSQL = cars.vehicleSQL()
    output = db.query(qSQL.statistics())

    return render_template('statistics.html', info=output)


# Modified sessions.py code with render template instaed of returning a html snippet
app.secret_key = 'BAD_SECRET_KEY' 

# Defines length of permanent sessions
app.permanent_session_lifetime = timedelta(minutes=1)

# I commented this so I understand the logic of logging in
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':

        # get the username and password inputted on the login form
        username = request.form.get('username')
        password = request.form.get('password')

        # Query from sql_queries method
        car_query = sql_queries()
        users = car_query.get('users', [])

        # Find matching user from DB results
        user = next((u for u in users if u.get('username') == username), None)

        # If the username and password have corrosponding matches in the database
        if user and user.get('password') == password:
            session.permanent = False

            # Store information from the user dictionary in session object
            session['role'] = user.get('role')
            session['first_name'] = user.get('first_name')
            session['last_name'] = user.get('last_name')

            # Redirect to get_email
            return redirect(url_for('get_email'))
        
        # If there is no match, 
        else:
            flash('Invalid username or password.')
            return redirect(url_for('login'))

    # Display the login form to begin with
    return render_template('login.html', cars={})

# If the role is obtained, display the correct template, otherwise redirect back to login
@app.route('/get_email')
def get_email():

    # Redirects based on role
    if "first_name" in session and "last_name" in session and "role" in session:
        if session["role"] == 'Buyer':
            return redirect(url_for('home', role=session['role'], first_name=session['first_name'], last_name=session['last_name']))
        if session["role"] == 'Owner':
            return redirect(url_for('all_vehicles', role=session['role'], first_name=session['first_name'], last_name=session['last_name']))
        else:
            return redirect(url_for('home', role=session['role'], first_name=session['first_name'], last_name=session['last_name']))
    else:
        return redirect(url_for('login'))

# Remove the role from the session and route back to the login page
@app.route('/delete_session')
def delete_session():
    session.pop('role', default=None)
    session.pop('first_name', default=None)
    session.pop('last_name', default=None)
    flash('You have been logged out.')
    return redirect(url_for('login'))


# Marks a part as installed and updates the database
@app.route('/install_part/<int:part_id>', methods=['POST'])
def install_part(part_id):
    vehicle_id = request.form.get('vehicle_id')

    # Connect to database and update part
    try:
        cur = db.mysql.connection.cursor()
        update_sql = "UPDATE csc206cars.parts SET status = 'Installed' WHERE partID = %s"
        cur.execute(update_sql, (part_id,))
        db.mysql.connection.commit()
        cur.close()
        flash('Part marked as Installed.')
    except Exception as e:
        flash(f'Error installing part: {e}')

    # Go back to vehicle details page when finished
    if vehicle_id:
        return redirect(url_for('vehicle_details', vehicle_id=vehicle_id))
    return redirect(url_for('home'))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
