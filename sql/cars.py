class vehicleSQL():

    # Allows display of model and manufacturer
    def all_vehicles(self):
        sql = '''SELECT
                    v.model_name,
                    m.manufacturer_name
                FROM
                    vehicles v
                INNER JOIN
                    manufacturers m 
                ON 
                    v.manufacturerID = m.manufacturerID
                ORDER BY 
                    m.manufacturer_name, v.model_name'''

        return sql

    # Selects the distinct manufacturer names
    def vehicle_names(self):
        sql = '''SELECT DISTINCT 
                    m.manufacturer_name,
                    m.manufacturerID
                FROM
                    vehicles
                INNER JOIN 
                    csc206cars.manufacturers m 
                ON 
                    vehicles.manufacturerID = m.manufacturerID;'''

        return sql

    # Selects the distinct vehicle types
    def vehicle_type(self):
        sql = '''SELECT DISTINCT 
                    m.vehicle_type_name,
                    m.vehicle_typeID
                FROM 
                    vehicles
                INNER JOIN
                    csc206cars.vehicletypes m 
                ON 
                    vehicles.vehicle_typeID= m.vehicle_typeID;'''

        return sql

    # Selects model names
    def vehicle_years(self):
        sql = '''SELECT DISTINCT
                    model_year
                FROM 
                    vehicles
                ORDER BY
                    model_year
                '''
        return sql

    # Selects fuel type
    def vehicle_fuel_type(self):
        sql = '''SELECT DISTINCT 
                    fuel_type
                FROM 
                    vehicles'''

        return sql

    # Select distinct colors
    def colors(self):
        sql = '''SELECT DISTINCT
                    c.color_name,
                    c.colorID
                FROM
                    vehicles
                INNER JOIN 
                    csc206cars.vehiclecolors v
                ON 
                    vehicles.vehicleID = v.vehicleID
                INNER JOIN
                    csc206cars.colors c
                ON
                    v.colorID = c.colorID;
                    '''

        return sql

    # Query figured out with ezra

    # passes filters dictionary 
    def sellable_vehicles(self, filters: dict | None = None):

        # First get all the information from the tables
        # Include concatednated colors ewwwwww
        sql_base = '''
            SELECT
                v.*,
                vcl.concatenated_colors,
                vtn.vehicle_type_name,
                m.manufacturer_name,
                pt.purchase_price AS purchase_price, 
                vpc.total_cost AS total_cost        
            FROM
                csc206cars.vehicles v
            LEFT JOIN
                csc206cars.manufacturers m
            ON
                v.manufacturerID = m.manufacturerID
            LEFT JOIN
                csc206cars.vehicletypes vtn
            ON
                v.vehicle_typeID = vtn.vehicle_typeID
            LEFT JOIN
                csc206cars.purchasetransactions pt
            ON
                v.vehicleID = pt.vehicleID
            LEFT JOIN
                (
                    SELECT
                        po.vehicleID,
                        SUM(p.cost) AS total_cost
                    FROM
                        csc206cars.partorders po
                    INNER JOIN
                        csc206cars.parts p
                    ON
                        po.part_orderID = p.part_orderID
                    GROUP BY
                        po.vehicleID
                ) AS vpc
            ON
                v.vehicleID = vpc.vehicleID
            LEFT JOIN
                (
                    SELECT
                        vc.vehicleID,
                        GROUP_CONCAT(c.color_name ORDER BY c.color_name ASC SEPARATOR ', ') AS concatenated_colors
                    FROM
                        csc206cars.vehiclecolors vc
                    INNER JOIN
                        csc206cars.colors c
                    ON
                        vc.colorID = c.colorID
                    GROUP BY
                        vc.vehicleID
                ) AS vcl
            ON
                v.vehicleID = vcl.vehicleID
        '''

        # Determines if vehicle is sellable
        where_conditions = [
            "v.vehicleID NOT IN (SELECT vehicleID FROM csc206cars.salestransactions)",
            '''v.vehicleID NOT IN (
                SELECT DISTINCT po.vehicleID
                FROM csc206cars.partorders po
                INNER JOIN csc206cars.parts p on po.part_orderID = p.part_orderID
                WHERE p.status != 'Installed'
            )'''
        ]

        # Applies filters using the filter key from app.py
        # If the filter is in the dictionary, add to where condition
        if filters:
            if 'manID' in filters:
                where_conditions.append(f"v.manufacturerID = {filters['manID']}")

            if 'vehicletypeID' in filters:
                where_conditions.append(f"v.vehicle_typeID = {filters['vehicletypeID']}")

            if 'modelname' in filters:
                where_conditions.append(f"v.model_name = '{filters['modelname']}'")

            if 'model_year' in filters:
                where_conditions.append(f"v.model_year = {filters['model_year']}")

            if 'fueltype' in filters:
                where_conditions.append(f"v.fuel_type = '{filters['fueltype']}'")


            # Ewwwww multiple colors
            color_condition = None
            if 'colorid' in filters:
                color_condition = f"vc.colorID = {filters['colorid']}"
            elif 'colorname' in filters:
                color_condition = f"c.color_name = '{filters['colorname']}'"

            if color_condition:
                color_exists_clause = f'''
                EXISTS (
                    SELECT 1
                    FROM csc206cars.vehiclecolors vc
                    INNER JOIN csc206cars.colors c ON vc.colorID = c.colorID
                    WHERE vc.vehicleID = v.vehicleID AND {color_condition}
                )
                '''
                where_conditions.append(color_exists_clause)

        # Combines sellable condtion with possible filters
        where_clause = "WHERE\n" + "\nAND ".join(where_conditions)

        # Lets assemble this silly query
        sql = f'''
            {sql_base}
            {where_clause}
            ORDER BY
                v.model_name DESC,
                m.manufacturer_name ASC
        '''
        return sql

    # 3 Queries below done with help of ma boi

    # Gets salespersons first and last name and joins them
    # Counts total vehichles, revenue, and average price
    def sale(self):
        sql = '''
            SELECT 
                u.userID, 
                CONCAT(u.first_name, ' ', u.last_name) AS salesperson, 
                COUNT(s.vehicleID) AS vehicles_sold, 
                SUM(pt.purchase_price) AS total_sold_price, 
            CASE WHEN 
                COUNT(s.vehicleID) > 0 
            THEN 
                SUM(pt.purchase_price)/COUNT(s.vehicleID) END AS avg_sale_price 
            FROM 
                salestransactions s 
            JOIN 
                users u 
            ON
                s.userID = u.userID 
            LEFT JOIN 
                purchasetransactions pt 
            ON 
                s.vehicleID = pt.vehicleID 
            GROUP BY 
                u.userID, u.first_name, u.last_name 
            ORDER BY 
                vehicles_sold DESC, 
                total_sold_price DESC;
            '''

        return sql

    # Gets the user first and last name and joins them together
    # Also gets the total number of vechiles sold
    def seller(self):
        sql = '''     
            SELECT 
                c.customerID, 
                CONCAT(c.first_name, ' ', c.last_name) AS seller_name, 
                COUNT(pt.vehicleID) AS vehicles_sold_to_dealer, 
                SUM(pt.purchase_price) AS total_paid 
            FROM 
                purchasetransactions pt 
            JOIN 
                customers c 
            ON 
                pt.customerID = c.customerID 
            GROUP BY 
                c.customerID, c.first_name, c.last_name 
            ORDER BY 
                vehicles_sold_to_dealer DESC, 
                total_paid ASC;
            '''
        return sql

    # Get the vendor information and calculates the number of parts, total money, and average cost
    def statistics(self):
        sql = '''
            SELECT 
                v.vendorID, 
                v.vendor_name, 
                SUM(p.quantity) AS parts_purchased, 
                SUM(p.cost * p.quantity) AS total_spent, 
        CASE WHEN 
            SUM(p.quantity) > 0 
        THEN 
            SUM(p.cost * p.quantity)/SUM(p.quantity) ELSE NULL END AS avg_cost_per_part 
        FROM 
            partorders po 
        JOIN 
            vendors v 
        ON 
            po.vendorID = v.vendorID 
        JOIN
            parts p 
        ON 
            p.part_orderID = po.part_orderID 
        GROUP BY 
            v.vendorID, 
            v.vendor_name 
        ORDER BY 
            parts_purchased DESC;
        '''
        return sql

    # Query returns the username, password, and role for the login information
    def users(self):
        sql = '''SELECT
                    username,
                    password,
                    role
                FROM
                    csc206cars.users'''

        return sql
