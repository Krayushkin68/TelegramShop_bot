import json
import random
import sqlite3
from string import ascii_letters, digits


def generate_coupon(length=15):
    coupon = random.choices(ascii_letters + digits, k=length)
    return ''.join(coupon)


def connect_db():
    try:
        connection = sqlite3.connect(r'DB/shop.db')
        connection.execute("PRAGMA foreign_keys = 1")
        return connection
    except sqlite3.Error as error:
        print('DB Error:', error)
        return False


def db_decorator(func):
    def wrapper(*args, **kwargs):
        con = connect_db()
        cursor = con.cursor()

        res = func(con, cursor, *args, **kwargs)

        cursor.close()
        con.close()
        return res

    return wrapper


@db_decorator
def create_tables(con: sqlite3.Connection, cursor: sqlite3.Cursor):
    categories_table = '''create table if not exists Categories (
                          name text primary key )'''

    product_table = '''create table if not exists Products (
                       id integer not null primary key,
                       category text references categories (name) on delete cascade on update cascade,
                       name text not null,
                       price integer not null,
                       content text not null)'''

    users_table = '''create table if not exists Users (
                     user_id integer not null primary key,
                     name text not null,
                     balance integer default 0,
                     spent integer default 0,
                     history text default '{"buy": [], "deposit": [], "referers": []}',
                     coupon text default '{"coupons": []}' )'''

    try:
        cursor.execute(categories_table)
        cursor.execute(product_table)
        cursor.execute(users_table)
        con.commit()
    except sqlite3.Error as error:
        print('DB Error:', error)
        return False
    return True


@db_decorator
def add_category(con: sqlite3.Connection, cursor: sqlite3.Cursor, category_name: str):
    query = 'insert or ignore into Categories values (?)'

    try:
        cursor.execute(query, (category_name,))
        con.commit()
    except sqlite3.Error as error:
        print('DB Error:', error)
        return False
    return True


@db_decorator
def del_category(con: sqlite3.Connection, cursor: sqlite3.Cursor, category_name: str):
    query = 'delete from Categories where name = (?)'

    try:
        cursor.execute(query, (category_name,))
        con.commit()
    except sqlite3.Error as error:
        print('DB Error:', error)
        return False
    return True


@db_decorator
def add_product(con: sqlite3.Connection, cursor: sqlite3.Cursor, product: list):
    query = 'insert into Products (category, name, price, content) values (?,?,?,?)'

    try:
        cursor.execute(query, tuple(product))
        con.commit()
    except sqlite3.Error as error:
        print('DB Error:', error)
        return False
    return True


@db_decorator
def del_product(con: sqlite3.Connection, cursor: sqlite3.Cursor, product):
    query = 'delete from Products where name = (?) and category = (?) and price = (?)'

    try:
        cursor.execute(query, tuple(product))
        con.commit()
    except sqlite3.Error as error:
        print('DB Error:', error)
        return False
    return True


@db_decorator
def delete_products(con: sqlite3.Connection, cursor: sqlite3.Cursor, product_ids: list):
    query = f"delete from Products where  id in ({', '.join(product_ids)})"
    try:
        cursor.execute(query)
        con.commit()
    except sqlite3.Error as error:
        print('DB Error:', error)
        return False
    return True


@db_decorator
def select_categories(con: sqlite3.Connection, cursor: sqlite3.Cursor):
    query = 'select name from Categories'
    cursor.execute(query)
    categories = [i[0] for i in cursor.fetchall()]
    return categories


@db_decorator
def check_category(con: sqlite3.Connection, cursor: sqlite3.Cursor, name):
    query = 'select name from Categories where name = (?)'
    cursor.execute(query, (name,))
    res = cursor.fetchone()
    if res:
        return res
    else:
        return False


@db_decorator
def select_all_products(con: sqlite3.Connection, cursor: sqlite3.Cursor):
    query = 'select * from Products order by category, name, price'
    cursor.execute(query)
    products = cursor.fetchall()
    products = [f'{str(p[0])};{str(p[1])};{str(p[2])};{str(p[3])};{str(p[4])}' for p in products]
    products.insert(0, 'id;category;name;price;content')
    products = '\n'.join(products)
    return products


@db_decorator
def select_products_by_category(con: sqlite3.Connection, cursor: sqlite3.Cursor, category):
    query = "select name, price, count(*) from Products where category=(?) group by category, name, price"
    cursor.execute(query, (category,))
    products = cursor.fetchall()
    return products


@db_decorator
def get_product(con: sqlite3.Connection, cursor: sqlite3.Cursor, category, name, price, quantity):
    query = "select id, content from Products where category=(?) and name = (?) and price = (?)"
    cursor.execute(query, (category, name, price))
    products = cursor.fetchmany(quantity)
    return products


@db_decorator
def add_user(con: sqlite3.Connection, cursor: sqlite3.Cursor, user: list):
    query = 'insert or ignore into Users (user_id, name) values (?,?)'
    try:
        cursor.execute(query, tuple(user))
        con.commit()
    except sqlite3.Error as error:
        print('DB Error:', error)
        return False
    return True


@db_decorator
def select_users_pretty(con: sqlite3.Connection, cursor: sqlite3.Cursor):
    query = 'select user_id, name from Users'
    cursor.execute(query)
    users = cursor.fetchall()
    head = ['ID        NAME']
    users_list = [f'{i[0]} {i[1]}' for i in users]
    users_list = '\n'.join(head + users_list)

    if users_list:
        return users_list
    else:
        return False


@db_decorator
def select_users_id(con: sqlite3.Connection, cursor: sqlite3.Cursor):
    query = 'select user_id from Users'
    cursor.execute(query)
    users = cursor.fetchall()
    users = [i[0] for i in users]
    if users:
        return users
    else:
        return False


@db_decorator
def check_user(con: sqlite3.Connection, cursor: sqlite3.Cursor, user_id):
    query = 'select user_id, name, balance, spent from Users where user_id = (?)'
    cursor.execute(query, (user_id,))
    res = cursor.fetchone()
    if res:
        return res
    else:
        return False


@db_decorator
def update_user(con: sqlite3.Connection, cursor: sqlite3.Cursor, user_id, balance=None, spent=None, history=None,
                coupon=None):
    user_info = 'select balance, spent, history, coupon from Users where user_id = (?)'
    cursor.execute(user_info, (user_id,))
    cur_balance, cur_spent, cur_history, cur_coupon = cursor.fetchone()

    if balance is not None:
        cur_balance = balance
    if spent is not None:
        cur_spent = spent
    if history is not None:
        cur_history = json.loads(cur_history)
        cur_history[history[0]].append(history[1])
        cur_history[history[0]] = cur_history[history[0]][-20:]
        cur_history = json.dumps(cur_history)
    if coupon is not None:
        cur_coupon = coupon

    query = 'update Users set balance = (?), spent = (?), history = (?), coupon = (?) where user_id = (?)'
    try:
        cursor.execute(query, (cur_balance, cur_spent, cur_history, cur_coupon, user_id))
        con.commit()
    except sqlite3.Error as error:
        print('DB Error:', error)
        return False
    return True


@db_decorator
def get_user_history(con: sqlite3.Connection, cursor: sqlite3.Cursor, user_id):
    query = 'select history from Users where user_id = (?)'
    cursor.execute(query, (user_id,))
    history = cursor.fetchone()[0]
    history = json.loads(history)
    return history


@db_decorator
def give_user_coupon(con: sqlite3.Connection, cursor: sqlite3.Cursor, user_id, coupon_value):
    query = 'select coupon from Users where user_id = (?)'
    cursor.execute(query, (user_id,))

    coupon = cursor.fetchone()[0]
    coupon = json.loads(coupon)
    generated_coupon = generate_coupon()
    coupon['coupons'].append((coupon_value, generated_coupon))
    coupon = json.dumps(coupon)

    update_user(user_id=user_id, coupon=coupon)

    return generated_coupon


@db_decorator
def use_user_coupon(con: sqlite3.Connection, cursor: sqlite3.Cursor, user_id, use_coupon):
    query = 'select coupon from Users where user_id = (?)'
    cursor.execute(query, (user_id,))

    coupons = cursor.fetchone()[0]
    coupons = json.loads(coupons)
    for c in coupons['coupons']:
        if c[1] == use_coupon:
            cursor.execute('select balance from Users where user_id = (?)', (user_id,))
            balance = cursor.fetchone()[0]
            balance += c[0]
            coupons['coupons'].remove(c)
            coupons = json.dumps(coupons)
            update_user(user_id=user_id, balance=balance, coupon=coupons)
            return c[0]
    return False
