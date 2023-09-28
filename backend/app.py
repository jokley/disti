from flask import Flask, json,jsonify,render_template, request, url_for, flash, redirect
from werkzeug.exceptions import abort
from datetime import datetime
import pytz
import psycopg2
import psycopg2.extras
from flask_cors import CORS
from flask_mqtt import Mqtt
from dotenv import load_dotenv
import sys
import os

load_dotenv()


def get_timestamp_now():
    TIMESTAMP_NOW = datetime.now().astimezone(pytz.timezone("Europe/Berlin")).isoformat()
    return TIMESTAMP_NOW

def get_timestamp_now_offset():
    TIMESTAMP_NOW_OFFSET = pytz.timezone("Europe/Berlin").utcoffset(datetime.now()).total_seconds()
    return TIMESTAMP_NOW_OFFSET

def get_timestamp_now_epoche():
    TIMESTAMP_NOW_EPOCHE = int(datetime.now().timestamp()+get_timestamp_now_offset())
    return TIMESTAMP_NOW_EPOCHE 

def get_db_connection():
    conn = psycopg2.connect(host='postgres',
                            database='postgres',
                            user=os.getenv("DOCKER_POSTGRES_INIT_USERNAME"),
                            password=os.getenv("DOCKER_POSTGRES_INIT_PASSWORD"))
    return conn

       
def get_post(post_id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory = psycopg2.extras.RealDictCursor)
    cur.execute('SELECT * FROM posts WHERE id = %s;',(post_id,))
    post = cur.fetchone()
    cur.close()
    conn.close()
    if post is None:
        abort(404)
    return post





app = Flask(__name__)
CORS(app)


app.config['MQTT_BROKER_URL'] = "172.16.238.12"
app.config['MQTT_BROKER_PORT'] = 1883
app.config['MQTT_USERNAME'] = os.getenv("DOCKER_MQTT_INIT_USERNAME")
app.config['MQTT_PASSWORD'] = os.getenv("DOCKER_MQTT_INIT_PASSWORD")
app.config['MQTT_KEEPALIVE'] = 10
app.config['MQTT_CLIENT_ID']= 'jokley_flask_mqtt'

app.secret_key = 'hi'

mqtt = Mqtt(app)


mqtt.subscribe("sensors/#")
  
@mqtt.on_message()
def handle_message(client, userdata, message):
#    if message.topic == "sensors/#":
      
    data = json.loads(message.payload.decode())
    app.logger.info(data)
    sName = data['name']
    sType = data['type']

    if data['type'] == "ds18b20":
        sTemp = data['temp']
        sHumi = 0
    elif data['type'] == "si7021":
        sTemp = data['temp']
        sHumi = data['humi']
       
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('INSERT INTO sensor (name, type, temp, humi)'
                'VALUES (%s, %s, %s, %s)',
                (sName, sType, sTemp, sHumi))
    conn.commit()
    cur.close()
    conn.close()


@mqtt.on_connect()
def handle_connect(client, userdata, flags, rc):
      mqtt.subscribe("sensors/#")
      app.logger.info('on_connect client : {} userdata :{} flags :{} rc:{}'.format(client, userdata, flags, rc))
      app.logger.info("connected")
      app.logger.info("topic subscribed sensors/#")
        

# @mqtt.on_subscribe()
# def handle_subscribe(client, userdata, mid, granted_qos):
#     print('on_subscribe client : {} userdata :{} mid :{} granted_qos:{}'.format(client, userdata, mid, granted_qos))


# @mqtt.on_message()
# def handle_message(client, userdata, message):
#     print('on_message client : {} userdata :{} message.topic :{} message.payload :{}'.format(
#     	client, userdata, message.topic, message.payload.decode()))

# @mqtt.on_disconnect()
# def handle_disconnect(client, userdata, rc):
#     print('on_disconnect client : {} userdata :{} rc :{}'.format(client, userdata, rc))
    

# @mqtt.on_log()
# def handle_logging(client, userdata, level, buf):
#      app.logger.info(level, buf)


@app.route('/')
def index():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory = psycopg2.extras.RealDictCursor)
    cur.execute('SELECT * FROM posts;')
    posts = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('index.html', posts=posts)


@app.route('/<int:post_id>')
def post(post_id):
    post = get_post(post_id)
    return render_template('post.html', post=post)


@app.route('/backend/create', methods=('GET', 'POST'))
def create():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']

        if not title:
            flash('Title is required!')
        else:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute('INSERT INTO posts (title, content) VALUES (%s, %s);',(title, content))
            conn.commit()
            cur.close()
            conn.close()
            return redirect(url_for('index'))

    return render_template('create.html')


@app.route('/<int:id>/edit', methods=('GET', 'POST'))
def edit(id):
    post = get_post(id)

    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']

        if not title:
            flash('Title is required!')
        else:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute('UPDATE posts SET title = %s, content = %s WHERE id = %s;',(title, content, id))
            conn.commit()
            cur.close()
            conn.close()
            return redirect(url_for('index'))

    return render_template('edit.html', post=post)


@app.route('/<int:id>/delete', methods=('POST',))
def delete(id):
    post = get_post(id)
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('DELETE FROM posts WHERE id = %s;', (id,))
    conn.commit()
    cur.close()
    conn.close()
    flash('"{}" was successfully deleted!'.format(post['title']))
    return redirect(url_for('index'))




@app.route('/time')
def time():
    return jsonify(get_timestamp_now_epoche(),get_timestamp_now(),get_timestamp_now_offset())


@app.route('/sensors', methods=['GET'])
def handle_sensor():
        
        FROM =request.args.get('from', default = get_timestamp_now_epoche()-36000, type = int)
        TO = request.args.get('to', default = get_timestamp_now_epoche(), type = int)

        VON = datetime.fromtimestamp(int(FROM)).isoformat()
        BIS = datetime.fromtimestamp(int(TO)).isoformat()  

        conn = get_db_connection()
        cur = conn.cursor(cursor_factory = psycopg2.extras.RealDictCursor)
        cur.execute('SELECT * FROM sensor where date between %s and %s order by date;',(VON, BIS))
        # cur.execute('''SELECT time_bucket('1 m', date) AS time,
        #                 avg(temp) as temp,
        #                 name
        #                 FROM sensor
        #                 where date between %s and %s
        #                 GROUP BY time,name
        #                 ORDER BY time;''',(VON, BIS))
        sensors = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify(sensors)


@app.route('/cars', methods=['GET'])
def handle_cars():
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory = psycopg2.extras.RealDictCursor)
        cur.execute('SELECT * FROM cars;')
        cars = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify(cars)
    


# @app.route('/cars', methods=['POST', 'GET'])
# def handle_cars():
#     if request.method == 'POST':
#         if request.is_json:
#             data = request.get_json()
#             new_car = CarsModel(name=data['name'], model=data['model'], doors=data['doors'])
#             db.session.add(new_car)
#             db.session.commit()
#             return {"message": f"car {new_car.name} has been created successfully."}
#         else:
#             return {"error": "The request payload is not in JSON format"}

#     elif request.method == 'GET':
#         all_cars = CarsModel.query.all()
#         # results = [
#         #     {
#         #         "name": car.name,
#         #         "model": car.model,
#         #         "doors": car.doors
#         #     } for car in cars]

#         return jsonify(cars_schema.dump(all_cars))


# @app.route('/cars/<car_id>', methods=['GET', 'PUT', 'DELETE'])
# def handle_car(car_id):
#     car = CarsModel.query.get_or_404(car_id)

#     if request.method == 'GET':
#         response = {
#             "name": car.name,
#             "model": car.model,
#             "doors": car.doors
#         }
#         return {"message": "success", "car": response}

#     elif request.method == 'PUT':
#         data = request.get_json()
#         car.name = data['name']
#         car.model = data['model']
#         car.doors = data['doors']
#         db.session.add(car)
#         db.session.commit()
#         return {"message": f"car {car.name} successfully updated"}

#     elif request.method == 'DELETE':
#         db.session.delete(car)
#         db.session.commit()
#         return {"message": f"Car {car.name} successfully deleted."}