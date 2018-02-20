import os
import logging
import requests
from csv import DictReader
from flask import Flask, jsonify
from json import decoder

app = Flask(__name__)

# Set up debug file and choose its logging level
logging.basicConfig(filename="Debug.log", level=logging.INFO)

def parse_data(product):
    """
    Function to format a product such that it's values are the correct data types
    """
    for key in product:
        if product[key] == "":
            product[key] = None
    try:
        product["price"] = float(product["price"])
    except (ValueError, TypeError, KeyError) as error:
        product["price"] = None
    try:
        if "y" in product["in_stock"]:
            product["in_stock"] = True
        elif "n" in product["in_stock"]:
            product["in_stock"] = False
        else:
            product["in_stock"] = None
    except TypeError:
        if isinstance(product["in_stock"],bool):
            # The value is already a bool
            pass
        else:
            logging.warning("Failed to parse data, invalid type")
            logging.warning("Data: {}".format(product["in_stock"]))
            logging.warning("Type: {}".format(type(product["in_stock"])))
            product["in_stock"]=None
    except KeyError:
        product["in_stock"]=None
    return product

def parse_csv(product_list):
    """
    Function to remove excess characters from products in the csv file
    then call the parse_data function to format the product.
    """
    for product in product_list:
        for key in product:
            product[key] = product[key].replace(' \"','').replace('\"','')
        product = parse_data(product)
    return product_list

def parse_json(product_list):
    """
    Wrapper to call the parse data function on the json data
    """
    for product in product_list:
        product = parse_data(product)
    return product_list
    
def startup():
    help_string = """
        The API is available at:
        http://localhost:5000/api/products/

        Example use:

        A GET request to http://localhost:5000/api/products/1234 would return
        the details of the product with id = 1234 (if it exists) in JSON format
        """
    print(help_string)
    if "products.csv" in os.listdir(os.getcwd()):
        #Fetch json products from aws
        aws_url = "https://s3-eu-west-1.amazonaws.com/pricesearcher-code-tests/python-software-developer/products.json"
        response = requests.get(aws_url)
        try:
            # Read the fetched data as json and call parse function
            # to standardise the data into the form we require
            product_list = parse_json(response.json())
        except decoder.JSONDecodeError:
            logging.warning("Failed to retrieve json products from AWS, could not decode data into JSON")
        # Check the json products keys
        keys = []
        for d in product_list:
            for key in d:
                if key not in keys:
                    keys.append(key)
        if set(keys) != set(["id", "name", "brand", "retailer", "price", "in_stock"]):
            logging.warning("Json products keys differ from required")
            logging.warning("Json keys: {}".format(list(keys)))
        # Use DictReader from csv module to turn the csv data into a python dictionary
        with open("products.csv") as csvfile:
            dr = DictReader(csvfile, delimiter=",")
            # Reassign the field names to match the json data
            dr.fieldnames = ["id", "name", "brand", "retailer", "price", "in_stock"]
            # Parse the data to fit our expected scheme and add it to the list of products
            product_list.extend(parse_csv([x for x in dr]))
        return product_list
    else:
        logging.warning("Please ensure the products.csv file is in the same directory as the app!")

product_list = startup()

@app.route('/api/products/<id>')
def get_products(id):
    chosen_product={}
    for product in product_list:
        if product["id"] == id:
            chosen_product = product
            break
    if chosen_product == {}:
        return product_error()
    return jsonify({"Product":chosen_product})

@app.route('/api/products/')
def product_error():
    return jsonify({"Product":{},"Message":"Please provide a valid id"})