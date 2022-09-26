import { Avatar, Card, CardContent, CardHeader, Divider, Grid, IconButton, LinearProgress, ListItemSecondaryAction, makeStyles, Menu, MenuItem, Stack} from "@mui/material";
import { useTheme } from '@mui/material/styles';
import DeviceThermostatOutlinedIcon from '@mui/icons-material/DeviceThermostatOutlined';
import DateRangeOutlinedIcon from '@mui/icons-material/DateRangeOutlined';
import SkipPreviousIcon from '@mui/icons-material/SkipPrevious';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import SkipNextIcon from '@mui/icons-material/SkipNext';
import React, { useEffect, useState } from "react";
import ExampleChart from "../components/LineGraph";
import {options, options_simple} from "../components/ChartOptions"
import useSWR from 'swr'
import { Box } from "@mui/system";
import { formatISO9075 } from "date-fns";
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import { CardActions, Collapse } from "@mui/material";
import { styled } from '@mui/material/styles';
import GaugeChart from "../components/charts/GaugeChart";
import BarChart from "../components/charts/BarChart";
import LineChart from "../components/charts/LineChart";
import Controls from "@components/controls/Controls";
import moment from 'moment'



/* const useStyles = makeStyles({
  root: {
    background: 'linear-gradient(45deg, #B9E4F5 30%, #72ADC4 90%)',
    border: 0,
    borderRadius: 3,
    boxShadow: '0 3px 5px 2px rgba(50, 105, 135, .3)',
    color: 'black',
    padding: '3 30px',
  },
  colorPrimary: {
    backgroundColor: '#E9E9E9'
  },
  bar: {
    borderRadius: 5,
    backgroundColor: '#72ADC4'
  }
  
}); */

const color00 = 'rgba(0, 153, 153,1)';
const color01 = 'rgba(0, 204, 204, 1)';
const color02 = 'rgba(0, 255, 255, 1)';
const color03 = 'rgba(153, 255, 255, 1)';
const color04 = 'rgba(102, 204, 255, 1)';
const color05= 'rgba(102, 153, 204, 1)';
const color06 = 'rgba(0, 176, 191  , 1)';
const color07 = 'rgba(204, 102, 153,1)';




export default function App() {


  const TimestampNow = Math.round(new Date().getTime()/1000);
  
  //const classes = useStyles();
  const theme = useTheme();
  
  
  const [from, setFrom] = useState(moment().add(-5,'hour').unix());
  const [to,setTo] =useState(moment().add(5,'hour').unix());
  const [timeStart,setTimeStart] = useState(moment().add(-5,'hour').unix());
  const [timeEnd,setTimeEnd] = useState(moment().add(5,'hour').unix());
  const [range, setRange] = useState(1);
  const [anchorEl, setAnchorEl] = useState(null);
  const [expanded, setExpanded] = React.useState(false);
  const open = Boolean(anchorEl);

  const [sensorLabels, setSensorLabels] = useState([]);

  const [boilerTopCurrent, setBoilerTopCurrent] = useState([]);
  const [boilerTopMin, setBoilerTopMin] = useState([]);
  const [boilerTopMax, setBoilerTopMax] = useState([]);
  const [boilerTopData, setBoilerTopData] = useState([]);

  const [coolerOutCurrent, setCoolerOutCurrent] = useState([]);
  const [coolerOutMin, setCoolerOutMin] = useState([]);
  const [coolerOutMax, setCoolerOutMax] = useState([]);
  const [coolerOutData, setCoolerOutData] = useState([]);
 
  
  const url = (`https://unrated-mallard-4700.dataplicity.io/api/sensors?from=${timeStart}&to=${timeEnd}`);

   
  const { data, error } = useSWR(url,{refreshInterval: 1000});

  useEffect(() => { 
 
    if (data){


      let dataFilter = [];
      
      dataFilter = data.filter(item => 
        (moment(item.date).unix() >= from && moment(item.date).unix() <= to))
      


      let SensorLabel = dataFilter.filter((item)=> item.name === 'Boiler Top').map((item)=> new Date(item.date).toLocaleString('DE-AT', { hour: '2-digit', minute: '2-digit'}));
      SensorLabel = SensorLabel.sort((a, b) => a - b );

      const SensorDataBoilerBottom = dataFilter.filter((item)=> item.name === 'Boiler Bottom').map((item)=> item.temp)
      const SensorDataBoilerBottomMax = Math.round(Math.max.apply(null, dataFilter.filter((item) =>  item.name === 'Boiler Bottom').map((item) => item.temp)))
      const SensorDataBoilerBottomMin =  Math.round(Math.min.apply(null, dataFilter.filter((item) =>  item.name === 'Boiler Bottom').map((item) => item.temp)))
      const SensorDataBoilerBottomCurrent=  Math.round(dataFilter.filter((item) =>  item.name === 'Boiler Bottom').map((item) => item.temp).slice(-1)[0])
    
      const SensorDataBoilerTop = dataFilter.filter((item)=> item.name === 'Boiler Top').map((item)=> item.temp)
      const SensorDataBoilerTopMax = Math.round(Math.max.apply(null, dataFilter.filter((item) =>  item.name === 'Boiler Top').map((item) => item.temp)))
      const SensorDataBoilerTopMin =  Math.round(Math.min.apply(null, dataFilter.filter((item) =>  item.name === 'Boiler Top').map((item) => item.temp)))
      const SensorDataBoilerTopCurrent=  Math.round(dataFilter.filter((item) =>  item.name === 'Boiler Top').map((item) => item.temp).slice(-1)[0])
      
      const SensorDataCoolerIn = dataFilter.filter((item)=> item.name === 'Cooler In').map((item)=> item.temp)
      const SensorDataCoolerInMax = Math.round(Math.max.apply(null, dataFilter.filter((item) =>  item.name === 'Cooler In').map((item) => item.temp)))
      const SensorDataCoolerInMin =  Math.round(Math.min.apply(null, dataFilter.filter((item) =>  item.name === 'Cooler In').map((item) => item.temp)))
      const SensorDataCoolerInCurrent=  Math.round(dataFilter.filter((item) =>  item.name === 'Cooler In').map((item) => item.temp).slice(-1)[0])
      
      const SensorDataCoolerOut = dataFilter.filter((item)=> item.name === 'Cooler Out').map((item)=> item.temp)
      const SensorDataCoolerOutMax = Math.round(Math.max.apply(null, dataFilter.filter((item) =>  item.name === 'Cooler Out').map((item) => item.temp)))
      const SensorDataCoolerOutMin =  Math.round(Math.min.apply(null, dataFilter.filter((item) =>  item.name === 'Cooler Out').map((item) => item.temp)))
      const SensorDataCoolerOutCurrent=  Math.round(dataFilter.filter((item) =>  item.name === 'Cooler Out').map((item) => item.temp).slice(-1)[0])
    
      setSensorLabels(SensorLabel);

      setBoilerTopData(SensorDataBoilerTop);
      setBoilerTopCurrent(SensorDataBoilerTopCurrent);
      setBoilerTopMin(SensorDataBoilerTopMin);
      setBoilerTopMax(SensorDataBoilerTopMax);

      setCoolerOutData(SensorDataCoolerOut);
      setCoolerOutCurrent(SensorDataCoolerOutCurrent);
      setCoolerOutMin(SensorDataCoolerOutMin);
      setCoolerOutMax(SensorDataCoolerOutMax);

      // setBoilerTopCurrent(44);
      // console.log(SensorDataBoilerTopCurrent)
      
    
    }

  },[data,from,to]);
  

  if (error) return <h1>Something went wrong!</h1>
  if (!data) return ( 
    <Box sx={{ width: '100%' , paddingBottom:1,paddingTop:1}}>
     <LinearProgress/>
     <h1> ... Loading Data</h1>
   </Box>
      );


                


  const handleClick = (event) => {
    setAnchorEl(event.currentTarget);
  };
  const handleClose = (event) => {
  
    setTimeStart(from)
    setTimeEnd(to)
    setAnchorEl(null);
  }
    
    const handleMenuClose = () =>{
      setAnchorEl(null);
    }
  

    const handleprevious = () => {
    
      const zoom = to - from;
      setFrom(from - zoom)
      setTo(to - zoom)
      if (from - zoom < timeStart){
        setTimeStart(from -  zoom);
        setTimeEnd(to - zoom );
        }
     
    
    };
    
    const handlenext = () => {
    
      const zoom = to - from;
      setFrom(from + zoom)
      setTo(to + zoom)
      if (to + zoom > timeEnd){
      setTimeStart(from +  zoom);
      setTimeEnd(to + zoom );
      }
    
    };

const handlePreSelection = (event) => {
  let _name = event.target.getAttribute("name")
  let _range = Number(event.target.getAttribute("value"))
  // _range -= 1
    

    setFrom(moment().add(-_range,'hour').unix());
    setTo(moment().unix());
}


const handelDateRangePickerFrom = (newValue) => {
  setFrom(moment(newValue).unix())

  if (newValue >= to) {
    setTo(moment(newValue).unix())
  }    
}

const handelDateRangePickerTo = (newValue) => {
  setTo(moment(newValue).unix())

    if (newValue <= from) {
      setFrom(moment(newValue).unix())
    }     
 }






  
  
  
  return (
    
    <div>
      <Grid  container
        direction="row"
        justifyContent="space-around"
        alignItems="center"
        sx={{paddingBottom:1,paddingTop:3}}
        >
            <Box sx={{ display: 'flex', alignItems: 'center', pl: 1, pb: 1 }}>
              <div>{new Date(moment.unix(from)).toLocaleString('DE-AT', {day: '2-digit', month: 'short',year: '2-digit', hour: '2-digit', minute: '2-digit'})}</div>
          <IconButton aria-label="previous"  onClick={handleprevious}>
            {theme.direction === 'rtl' ? <SkipNextIcon /> : <SkipPreviousIcon />}
          </IconButton>
 
          <IconButton id="basic-button"
          aria-controls="basic-menu"
          aria-haspopup="true"
          aria-expanded={open ? 'true' : undefined}
          onClick={handleClick}
          >
             <DateRangeOutlinedIcon  />
             </IconButton>
              <Menu
                id="basic-menu"
                anchorEl={anchorEl}
                open={open}
                onClose={handleMenuClose}
                MenuListProps={{
                  'aria-labelledby': 'basic-button',
                }}
              >
              <Controls.BasicDateRangePicker
                from={from}
                to={to}
                onChangeFrom={handelDateRangePickerFrom}
                onChangeTo={handelDateRangePickerTo}
              
              />
                <MenuItem value="1" onClick={handlePreSelection}>Last 1 hour</MenuItem>
                <MenuItem value="3" onClick={handlePreSelection}>Last 3 hours</MenuItem>
                <MenuItem value="6" onClick={handlePreSelection}>Last 6 hours</MenuItem>
                <MenuItem value="12" onClick={handlePreSelection}>Last 12 hours</MenuItem>
                <MenuItem value="24" onClick={handlePreSelection}>Last 1 day</MenuItem>
                <MenuItem value="48" onClick={handlePreSelection}>Last 2 days</MenuItem>
                <Divider />
                 <MenuItem>
                 <Controls.Button 
                  onClick={handleClose}
                  text={'Übernehmen'}
                  />
                 </MenuItem>
              </Menu>  

              <IconButton aria-label="next"  onClick={handlenext}>
            {theme.direction === 'rtl' ? <SkipPreviousIcon /> : <SkipNextIcon />}
          </IconButton>
          <div>{new Date(moment.unix(to)).toLocaleString('DE-AT', {day: '2-digit', month: 'short',year: '2-digit', hour: '2-digit', minute: '2-digit'})}</div>
        </Box>
    
      </Grid>
      <Grid  container
         direction="row"
         justifyContent="center"
         alignItems="center"
         style={{ gap: 15}}>
      
      {/*+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++ */}
      <Grid item xs={9} sm={9} md={4.5}>
      <Box
          sx={{
            bgcolor: 'background.paper',
            boxShadow: 1,
            borderRadius: 1,
            p: 2,
            //  width: 350 ,
             hight: 200,
          }}
          >
        <Grid 
          container
          justifyContent="space-between"
          alignItems="center"
        >
          <Grid>
            <Box sx={{ color: 'text.secondary' , display: 'inline'}}>Boiler Top</Box>
          </Grid>
          <Grid>
            <Box sx={{ color: 'text.primary', fontSize: 34, fontWeight: 'medium' }}>
            {`${boilerTopCurrent}°C`}
            </Box>
          </Grid>
        </Grid>
        <GaugeChart data={[70,10,10,10]} 
                    data1={[boilerTopCurrent, 100-boilerTopCurrent]} 
                    needleValue={boilerTopCurrent}   
                    labels={['','Vorlauf','Mittellauf','Nachlauf']} 
                    color={[color04,color07,color06,color05]}
                    color1={[color01,'white']}  
                    rotation={0} />
          <Box sx={{ color: 'text.secondary', fontSize: 12 }}>
          <p></p>
          {`Min: ${boilerTopMin}°C '      'Max: ${boilerTopMax}°C`} 
          </Box>
      </Box>
      </Grid>

      {/*+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++ */}
      <Grid item xs={9} sm={9} md={4.5}>
      <Box
          sx={{
            bgcolor: 'background.paper',
            boxShadow: 1,
            borderRadius: 1,
            p: 2,
            //  width: 300 ,
             hight: 200,
          }}
          >
        <Grid 
          container
          justifyContent="space-between"
          alignItems="center"
        >
          <Grid>
            <Box sx={{ color: 'text.secondary' , display: 'inline'}}>Cooler Out</Box>
          </Grid>
          <Grid>
            <Box sx={{ color: 'text.primary', fontSize: 34, fontWeight: 'medium' }}>
            {`${coolerOutCurrent}°C`}
            </Box>
          </Grid>
        </Grid>
        <BarChart 
                  bereich1={[18]} 
                  bereich2={[4]}
                  bereich3={[8]}
                  labels={['Value','Temperature']} 
                  needleValue={coolerOutCurrent}  
                  />
                  <p></p>
          <Box sx={{ color: 'text.secondary', fontSize: 12 }}>
              {`Min: ${coolerOutMin}°C        Max: ${coolerOutMax}°C`} 
          </Box>
       
      </Box>
      
      </Grid>

    </Grid>

    
    
   

  
      
     
      <p></p>
     
       

      <Grid  container
        //direction="column"
        //columns={{ xs: 4, sm: 8, md: 12 }}
        justifyContent="space-around"
        alignItems="center"
        style={{ gap: 15 }}>
        
  


      
     
      <Grid Grid item xs={9} sm={9} md={9.1}>
      <Card >
      <CardHeader 
        avatar={
          <Avatar  variant="rounded" style={{color:'#B9E4F5', background:' #72ADC4'}}>
           <DeviceThermostatOutlinedIcon />
        </Avatar>
        }
        
        title={`Boiler Top: ${boilerTopCurrent}°C`}
        subheader={`Min: ${boilerTopMin}°C  Max: ${boilerTopMax}°C`} 
      />
      <CardContent>
      <LineChart  label ='Boiler Top' data={boilerTopData} labels={sensorLabels} />
      </CardContent>
      </Card>
      </Grid>



    
      </Grid>
     
    </div>
  );
}
