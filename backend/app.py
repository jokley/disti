from flask import Flask, json, render_template, request,jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
from datetime import datetime
import pytz
from flask_cors import CORS
from flask_mqtt import Mqtt


#TIMESTAMP_NOW = datetime.now().astimezone(pytz.timezone("Europe/Berlin")).isoformat()
#TIMESTAMP_NOW_OFFSET = pytz.timezone("Europe/Berlin").utcoffset(datetime.now()).total_seconds()
#TIMESTAMP_NOW_EPOCHE = int(datetime.now().timestamp()+TIMESTAMP_NOW_OFFSET)  

def get_timestamp_now():
    TIMESTAMP_NOW = datetime.now().astimezone(pytz.timezone("Europe/Berlin")).isoformat()
    return TIMESTAMP_NOW

def get_timestamp_now_offset():
    TIMESTAMP_NOW_OFFSET = pytz.timezone("Europe/Berlin").utcoffset(datetime.now()).total_seconds()
    return TIMESTAMP_NOW_OFFSET

def get_timestamp_now_epoche():
    TIMESTAMP_NOW_EPOCHE = int(datetime.now().timestamp()+get_timestamp_now_offset())
    return TIMESTAMP_NOW_EPOCHE 


app = Flask(__name__)
CORS(app)

app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:postgres@postgres/flasksql'
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

app.config['MQTT_BROKER_URL'] = "172.16.238.12"
app.config['MQTT_BROKER_PORT'] = 1883
app.config['MQTT_KEEPALIVE'] =60


app.secret_key = 'hi'

db = SQLAlchemy(app)
ma = Marshmallow(app)
mqtt = Mqtt(app)
#mqtt.subscribe("/sensors")


class Sensor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    type = db.Column(db.String(80), nullable=False)
    temp = db.Column(db.Float(2), nullable=True)
    humi = db.Column(db.Float(2), nullable=True)
    date = db.Column(db.DateTime(), nullable=False)

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

class CarSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = CarsModel
        ordered = True

car_schema = CarSchema()
cars_schema = CarSchema(many=True)

    
@mqtt.on_message()
def handle_message(client, userdata, message):
   if message.topic == "/sensors":
       #print(message.payload.decode())
       data = json.loads(message.payload.decode())
       if data['type'] == "ds18b20":
           new_sensor =  Sensor(name=data['name'],type=data['type'], temp=data['temp'],date=get_timestamp_now()) 
       elif data['type'] == "si7021":
           new_sensor =  Sensor(name=data['name'],type=data['type'],temp=data['temp'],humi=data['humi'],date=get_timestamp_now())   
       
       db.session.add(new_sensor)
       db.session.commit()


# @mqtt.on_connect()
# def handle_connect(client, userdata, flags, rc):
#     print('on_connect client : {} userdata :{} flags :{} rc:{}'.format(client, userdata, flags, rc))
#     mqtt.subscribe("/sensors")
        

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
#     print(level, buf)



@app.route('/')
def home():
    return '<a href="/addperson"><button> Click here </button></a>'

@app.route('/time')
def time():
    return jsonify(get_timestamp_now_epoche(),get_timestamp_now(),get_timestamp_now_offset())

 
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


@app.route('/sensors', methods=['POST', 'GET'])
def handle_senors():
    if request.method == 'POST':
        if request.is_json:
            data = request.get_json()
            if data['type'] == "ds18b20":
                new_sensor =  Sensor(name=data['name'],type=data['type'], temp=data['temp'],date=get_timestamp_now()) 
            elif data['type'] == "si7021":
                new_sensor =  Sensor(name=data['name'],type=data['type'],temp=data['temp'],humi=data['humi'],date=get_timestamp_now())   

            db.session.add(new_sensor)
            db.session.commit()
            return {"message": f"sensor {new_sensor.name} has been created successfully."}
        else:
            return {"error": "The request payload is not in JSON format"}

    elif request.method == 'GET':
        FROM =request.args.get('from', default = get_timestamp_now_epoche()-36000, type = int)
        TO = request.args.get('to', default = get_timestamp_now_epoche(), type = int)

        VON = datetime.fromtimestamp(int(FROM + get_timestamp_now_offset())).isoformat()
        BIS = datetime.fromtimestamp(int(TO + get_timestamp_now_offset())).isoformat()  

        all_senors = Sensor.query.filter(Sensor.date >= VON).filter(Sensor.date<=BIS).order_by(Sensor.date).all()
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
            sensor.date = get_timestamp_now()
        elif data['type'] == "si7021":
            sensor.name = data['name']
            sensor.temp = data['temp']
            sensor.humi = data['humi']
            sensor.date = get_timestamp_now()

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
        all_cars = CarsModel.query.all()
        # results = [
        #     {
        #         "name": car.name,
        #         "model": car.model,
        #         "doors": car.doors
        #     } for car in cars]

        return jsonify(cars_schema.dump(all_cars))


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
    
#if __name__ == "__main__":
    #app.run(host="0.0.0.0",port=5001, debug=True)
     
        
        


