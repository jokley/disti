import { Button, Card, Grid, makeStyles } from "@material-ui/core";
import React, { useState } from "react";
import ExampleChart from "../components/LineGraph";
import {options} from "../components/ChartOptions"
import useSWR from 'swr'

const useStyles = makeStyles({
  root: {
    background: 'linear-gradient(45deg, #B9E4F5 30%, #72ADC4 90%)',
    border: 0,
    borderRadius: 3,
    boxShadow: '0 3px 5px 2px rgba(50, 105, 135, .3)',
    color: 'black',
    padding: '3 30px',
  },
});


const TimestampNow = Math.round(new Date().getTime()/1000);


export default function App() {
  
  
  
  const classes = useStyles();
  
  const [to,setTo] = useState(TimestampNow);
  const [from, setFrom] = useState(TimestampNow-3600);


  const handleData = () => {
    setFrom(TimestampNow-36000)

  };
  const url = (`${process.env.backendUrl}/sensors?from=${from}&to=${to}`);

  const { data, error } = useSWR(url);

  if (error) return <h1>Something went wrong!</h1>
  if (!data) return <h1>Loading...</h1>

  const SensorDataBoilerTop = data.filter((item)=> item.name === 'Boiler Top').map((item)=> item.temp)
  const SensorDataCoolerIn = data.filter((item)=> item.name === 'Cooler In').map((item)=> item.temp)
  const SensorDataCoolerOut = data.filter((item)=> item.name === 'Cooler Out').map((item)=> item.temp)
  const SensorLabel = data.filter((item)=> item.name === 'Boiler Top').map((item)=> new Date (item.date).toLocaleTimeString());
  
  
  return (
    <div className="App">
      
      <Button className={classes.root} onClick={handleData}> Data Random</Button>
      <Grid  container
        direction="row"
        justifyContent="space-around"
        alignItems="center">
      <Card  >
      <ExampleChart label ='Boiler Top' data={SensorDataBoilerTop} labels={SensorLabel} options={options} />
      </Card>
      <Card >
      <ExampleChart label ='Cooler In' data={SensorDataCoolerIn} labels={SensorLabel} options={options} />
      </Card>
      <Card >
      <ExampleChart label ='Cooler Out' data={SensorDataCoolerOut} labels={SensorLabel} options={options} />
      </Card>
      </Grid>
 
    </div>
  );
}
