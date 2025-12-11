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
        'customers': vSQL.customers(),
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

    # For Buyers, show all unsold vehicles otherwise see sellable vehicles
    if session.get('role') == 'Buyer':
        output = db.query(qSQL.unsold_vehicles(filters if filters else None))
    else:
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

    # Determine sale eligibility; asked Gemini for help on this logic
    sold = buyer is not None
    all_parts_installed = True
    for p in parts or []:
        if p.get('status') != 'Installed':
            all_parts_installed = False
            break
    eligible_for_sale = (not sold) and all_parts_installed

    return render_template('details.html', car=car, parts=parts, seller=seller, buyer=buyer, eligible_for_sale=eligible_for_sale)

# Page to select a customer with dynamic routing for buy or sell
@app.route('/select_customer/<int:vehicle_id>/<action>', methods=['GET', 'POST'])
def select_customer(vehicle_id, action):

    vSQL = cars.vehicleSQL()
    customers = db.query(vSQL.customers())

    # This is to display the a newly created customer(with help from Gemini ofc)
    selected_customer_id = request.args.get('selected_customer_id', default=None, type=int)

    # If posting back, redirect to buy or sell page with selected customer
    if request.method == 'POST':
        cust_id = request.form.get('customerID', type=int)
        if not cust_id:
            flash('Please select a customer to continue.')
        else:
            if action == 'sell':
                # For selling, the sell page itself collects customer and date
                return redirect(url_for('sell_vehicle', vehicle_id=vehicle_id))
            else:
                return redirect(url_for('buy_vehicle', customer_id=cust_id, vehicle_id=vehicle_id))

    return render_template('select_customer.html', customers=customers, vehicle_id=vehicle_id, action=action, selected_customer_id=selected_customer_id)


# Buy vehicle page
@app.route('/buy_vehicle/<int:customer_id>/<int:vehicle_id>', methods=['GET'])
def buy_vehicle(customer_id, vehicle_id):
    salesperson_name = None
    salesperson_id = None

    # Get the salesperson name 
    if session.get('first_name') and session.get('last_name'):
        salesperson_name = f"{session.get('first_name')} {session.get('last_name')}"

    # Get the userID
    try:
        cur = db.mysql.connection.cursor()
        cur.execute("SELECT userID FROM csc206cars.salestransactions WHERE vehicleID = %s LIMIT 1", (vehicle_id,))
        row = cur.fetchone()
        if row:
            salesperson_id = row[0]
        cur.close()
    except Exception:
        salesperson_id = None

    # Get vehicle details 
    qSQL = cars.vehicleSQL()
    output = db.query(qSQL.vehicle_details(vehicle_id))
    car = output[0] if output else None

    return render_template('buy_vehicle.html',
        customer_id=customer_id,
        vehicle_id=vehicle_id,
        salesperson_name=salesperson_name,
        salesperson_id=salesperson_id,
        car=car,
    )


# Sell vehicle page
@app.route('/sell_vehicle/<int:vehicle_id>', methods=['GET', 'POST'])
def sell_vehicle(vehicle_id):

    
    qSQL = cars.vehicleSQL()
    customers = db.query(qSQL.customers())

    # Get the customer & sale date
    if request.method == 'POST':
        cust_id = request.form.get('customerID', type=int)
        sale_date = request.form.get('sale_date')
        if not cust_id or not sale_date:
            flash('Please select a customer and enter a sale date.')
        else:
            flash('Sale details captured. Completing sale coming soon.')
            return redirect(url_for('vehicle_details', vehicle_id=vehicle_id))

    return render_template('sell_vehicle.html', customers=customers, vehicle_id=vehicle_id)


    
# Create a new customer(This format is based on asking Gemini for how to do this)
@app.route('/create_customer', methods=['GET', 'POST'])
def create_customer():

    vehicle_id = request.args.get('vehicle_id', default=0, type=int)
    action = request.args.get('action', default='buy')

    if request.method == 'POST':

        # Required fields
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        id_number = request.form.get('id_number')
        phone_number = request.form.get('phone_number')

        # Address fields
        street = request.form.get('street')
        city = request.form.get('city')
        state = request.form.get('state')
        postal_code = request.form.get('postal_code')

        # Optional fields
        email_address = request.form.get('email_address') or None
        business_name = request.form.get('business_name') or None


        # Basic validation for required fields
        missing = []
        for key, val in {
            'First Name': first_name,
            'Last Name': last_name,
            'ID Number': id_number,
            'Phone Number': phone_number,
            'Street': street,
            'City': city,
            'State': state,
            'Postal Code': postal_code,
        }.items():
            if not val:
                missing.append(key)


        if missing:
            flash(f"Missing required fields: {', '.join(missing)}")
            return render_template('create_customer.html', vehicle_id=vehicle_id, action=action)

        # Insert into database
        try:
            cur = db.mysql.connection.cursor()

            insert_sql = (
                "INSERT INTO csc206cars.customers "
                "(first_name, last_name, id_number, phone_number, email_address, street, city, state, postal_code, business_name) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
            )
            cur.execute(insert_sql, (
                first_name,
                last_name,
                id_number,
                phone_number,
                email_address,
                street,
                city,
                state,
                postal_code,
                business_name,
            ))
            db.mysql.connection.commit()
            # Get the newly inserted customer's id
            new_customer_id = cur.lastrowid
            cur.close()
            flash('Customer created successfully.')
            # Redirect back to select page with the newly created customer pre-selected
            return redirect(url_for('select_customer', vehicle_id=vehicle_id, action=action, selected_customer_id=new_customer_id))
        except Exception as e:
            flash(f'Error creating customer: {e}')
            return render_template('create_customer.html', vehicle_id=vehicle_id, action=action)
        
    return render_template('create_customer.html', vehicle_id=vehicle_id, action=action)

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
