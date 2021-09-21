from flask import Flask, json, render_template, request,jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
from datetime import datetime
import pytz
from flask_cors import CORS
from flask_mqtt import Mqtt


TIMESTAMP_NOW = datetime.now().astimezone(pytz.timezone("Europe/Berlin")).isoformat()
TIMESTAMP_NOW_OFFSET = pytz.timezone("Europe/Berlin").utcoffset(datetime.now()).total_seconds()
TIMESTAMP_NOW_EPOCHE = int(datetime.now().timestamp()+TIMESTAMP_NOW_OFFSET)  


app = Flask(__name__)
CORS(app)

app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:postgres@postgres/flasksql'
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

app.config['MQTT_BROKER_URL'] = "127.0.0.1"
app.config['MQTT_BROKER_PORT'] = 1883
app.config['MQTT_KEEPALIVE'] =20


app.secret_key = 'hi'

db = SQLAlchemy(app)
ma = Marshmallow(app)
mqtt = Mqtt(app)

class Sensor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    type = db.Column(db.String(80), nullable=False)
    temp = db.Column(db.Float(2), nullable=True)
    humi = db.Column(db.Float(2), nullable=True)
    date = db.Column(db.DateTime(), default=TIMESTAMP_NOW,onupdate=TIMESTAMP_NOW)

    # def __init__(self, name, type,temp,humi=None):
    #     self.name = name
    #     self.type = type
    #     self.temp = temp
    #     self.humi = humi
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
       

class SensorSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Sensor
        ordered = True

sensor_schema = SensorSchema()
sensors_schema = SensorSchema(many=True)
    

class People(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pname = db.Column(db.String(80), unique=True, nullable=False)
    color = db.Column(db.String(120), nullable=False)
    

    def __init__(self, pname, color):
        self.pname = pname
        self.color = color

class PeopleSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = People
        ordered = True

people_schema = PeopleSchema()
poeples_schema = PeopleSchema(many=True)

class CarsModel(db.Model):
    __tablename__ = 'cars'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String())
    model = db.Column(db.String())
    doors = db.Column(db.Integer())

    def __init__(self, name, model, doors):
        self.name = name
        self.model = model
        self.doors = doors

    def __repr__(self):
        return f"<Car {self.name}>"


@mqtt.on_connect()
def handle_connect(client, userdata, flags, rc):
    mqtt.subscribe("/sensors")
  

@mqtt.on_message()
def handle_message(client, userdata, message):
    if message.topic == "/sensorsss":
        data = json.loads(message.payload)
        if data['type'] == "ds18b20":
            new_sensor =  Sensor(name=data['name'],type=data['type'], temp=data['temp']) 
        elif data['type'] == "si7021":
            new_sensor =  Sensor(name=data['name'],type=data['type'],temp=data['temp'],humi=data['humi'])   

        db.session.add(new_sensor)
        db.session.commit()
  
# @mqtt.on_subscribe()
# def handle_subscribe(client, userdata, mid, granted_qos):
#     print('on_subscribe client : {} userdata :{} mid :{} granted_qos:{}'.format(client, userdata, mid, granted_qos))

# @mqtt.on_disconnect()
# def handle_disconnect(client, userdata, rc):
#     print('on_disconnect client : {} userdata :{} rc :{}'.format(client, userdata, rc))
    
# @mqtt.on_log()
# def handle_logging(client, userdata, level, buf):
#     print(level, buf)



@app.route('/')
def home():
    return '<a href="/addperson"><button> Click here </button></a>'

@app.route('/time')
def time():
    return jsonify(TIMESTAMP_NOW_EPOCHE,TIMESTAMP_NOW,TIMESTAMP_NOW_OFFSET)

 
@app.route("/persons")
def get_persons():
    all_people = People.query.all()
    return jsonify(poeples_schema.dump(all_people))


@app.route("/addperson")
def addperson():
    return render_template("index.html")


@app.route("/personadd", methods=['POST'])
def personadd():
    pname = request.form["pname"]
    color = request.form["color"]
    entry = People(pname, color)
    db.session.add(entry)
    db.session.commit()

    return render_template("index.html")


@app.route('/senors', methods=['POST', 'GET'])
def handle_senors():
    if request.method == 'POST':
        if request.is_json:
            data = request.get_json()
            if data['type'] == "ds18b20":
                new_sensor =  Sensor(name=data['name'],type=data['type'], temp=data['temp']) 
            elif data['type'] == "si7021":
                new_sensor =  Sensor(name=data['name'],type=data['type'],temp=data['temp'],humi=data['humi'])   

            db.session.add(new_sensor)
            db.session.commit()
            return {"message": f"sensor {new_sensor.name} has been created successfully."}
        else:
            return {"error": "The request payload is not in JSON format"}

    elif request.method == 'GET':
        FROM =request.args.get('from', default = TIMESTAMP_NOW_EPOCHE-36000, type = int)
        TO = request.args.get('to', default = TIMESTAMP_NOW_EPOCHE, type = int)

        VON = datetime.fromtimestamp(int(FROM + TIMESTAMP_NOW_OFFSET)).isoformat()
        BIS = datetime.fromtimestamp(int(TO + TIMESTAMP_NOW_OFFSET)).isoformat()  

        all_senors = Sensor.query.filter(Sensor.date >= VON).filter(Sensor.date<=BIS).all()
    return jsonify(sensors_schema.dump(all_senors))


@app.route('/senors/<senors_id>', methods=['GET', 'PUT', 'DELETE'])
def handle_sensor(senors_id):
    sensor = Sensor.query.get_or_404(senors_id)

    if request.method == 'GET':
        response = {
            "name": sensor.name,
            "type": sensor.type,
            "temp": sensor.temp,
            "humi": sensor.humi,
            "date": sensor.date
        }
        return {"message": "success", "sensor": response}

    elif request.method == 'PUT':
        data = request.get_json()
        if data['type'] == "ds18b20":
            sensor.name = data['name']
            sensor.temp = data['temp']
        elif data['type'] == "si7021":
            sensor.name = data['name']
            sensor.temp = data['temp']
            sensor.humi = data['humi']

        db.session.add(sensor)
        db.session.commit()
        return {"message": f"sensor {sensor.name} successfully updated"}

    elif request.method == 'DELETE':
        db.session.delete(sensor)
        db.session.commit()
        return {"message": f"sensor {sensor.name} successfully deleted."}


@app.route('/cars', methods=['POST', 'GET'])
def handle_cars():
    if request.method == 'POST':
        if request.is_json:
            data = request.get_json()
            new_car = CarsModel(name=data['name'], model=data['model'], doors=data['doors'])
            db.session.add(new_car)
            db.session.commit()
            return {"message": f"car {new_car.name} has been created successfully."}
        else:
            return {"error": "The request payload is not in JSON format"}

    elif request.method == 'GET':
        cars = CarsModel.query.all()
        results = [
            {
                "name": car.name,
                "model": car.model,
                "doors": car.doors
            } for car in cars]

        return {"count": len(results), "cars": results}

@app.route('/cars/<car_id>', methods=['GET', 'PUT', 'DELETE'])
def handle_car(car_id):
    car = CarsModel.query.get_or_404(car_id)

    if request.method == 'GET':
        response = {
            "name": car.name,
            "model": car.model,
            "doors": car.doors
        }
        return {"message": "success", "car": response}

    elif request.method == 'PUT':
        data = request.get_json()
        car.name = data['name']
        car.model = data['model']
        car.doors = data['doors']
        db.session.add(car)
        db.session.commit()
        return {"message": f"car {car.name} successfully updated"}

    elif request.method == 'DELETE':
        db.session.delete(car)
        db.session.commit()
        return {"message": f"Car {car.name} successfully deleted."}

db.create_all()

    
