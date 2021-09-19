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

const rnd = () => Math.floor(Math.random() * 20) + 1;

export default function App() {

  const url = ('http://127.0.0.1:5000/senors/1');
 

  const classes = useStyles();
  
  const [data1, setData1] = useState([1, 2, 3, 4, 5, 6]);
  const [data2, setData2] = useState([1, 2, 3, 4, 5, 6]);
  const [data3, setData3] = useState([1, 2, 3, 4, 5, 6]);
  const [labels,setLabels]= useState(["Red", "Blue", "Yellow", "Green", "Purple", "Orange"]);
 
  const handleData = () => {
    setData1([rnd(), rnd(), rnd(), rnd(), rnd(), rnd()]);
    setData2([rnd(), rnd(), rnd(), rnd(), rnd(), rnd()]);
    setData3([rnd(), rnd(), rnd(), rnd(), rnd(), rnd()]);
    

    setLabels(["Red", "Blue", "Yellow", "Green", "Purple", "Orange"]);
  };

  const { data, error } = useSWR(url);

  if (error) return <h1>Something went wrong!</h1>
  if (!data) return <h1>Loading...</h1>

  return (
    <div className="App">
     
      <Button className={classes.root} onClick={handleData}> Data Random</Button>
      <Grid  container
  direction="row"
  justifyContent="space-around"
  alignItems="center">
      <Card  >
      <ExampleChart data={data1} labels={labels} options={options} />
      </Card>
      <Card >
      <ExampleChart data={data2} labels={labels} options={options} />
      </Card>
      <Card >
      <ExampleChart data={data3} labels={labels} options={options} />
      </Card>
      </Grid>
      
      

    </div>
  );
}
