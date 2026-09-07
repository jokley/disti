import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))
from disti.repository import Repository


SCHEMA = """
CREATE TABLE sensors(id text primary key,name text,sensor_type text,enabled boolean);
CREATE TABLE sensor_calibrations(id text primary key,sensor_id text,version text,model text,points text,slope real,offset real,active boolean,created_at text,finalized_at text,activated_at text);
CREATE TABLE distillation_runs(id text primary key,run_type text,recipe_name text,batch_name text,notes text,status text,started_at text,ended_at text);
CREATE TABLE sensor_measurements(id text,time text,run_id text,sensor_id text,measurement_type text,raw_value real,raw_mv real,value real,unit text,temperature real,calibration_id text,quality text,metadata text);
CREATE TABLE fractions(id text primary key,run_id text,fraction_number integer,fraction_type text,operator_notes text,started_at text,ended_at text);
CREATE TABLE actuator_events(id text primary key,time text,run_id text,actuator_id text,event_type text,status text,details text);
"""


@pytest.fixture
def repo(tmp_path):
    path = tmp_path / "disti.db"
    connection = sqlite3.connect(path); connection.executescript(SCHEMA); connection.close()
    return Repository(lambda: sqlite3.connect(path), sqlite=True)
