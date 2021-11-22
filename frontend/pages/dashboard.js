import { Avatar, Card, CardContent, CardHeader, Grid, IconButton, LinearProgress, makeStyles, Menu, MenuItem} from "@mui/material";
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
import { getSession, signIn } from "next-auth/client";



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







export default function App() {

  const [loading, setloading] = useState(true)


  
  const TimestampNow = Math.round(new Date().getTime()/1000);
  
  //const classes = useStyles();
  const theme = useTheme();
  
  const [to,setTo] = useState(TimestampNow);
  const [from, setFrom] = useState(TimestampNow-3600);
  const [range, setRange] = useState(1);
  const [anchorEl, setAnchorEl] = useState(null);
  const [expanded, setExpanded] = React.useState(false);
  const open = Boolean(anchorEl);
  
 
 
  
  const url = (`https://unrated-mallard-4700.dataplicity.io/api/sensors?from=${from}&to=${to}`);

   
  const { data, error } = useSWR(url,{refreshInterval: 1000});
  

  // useEffect(()=>{
  //   const securePage = async() => {
  //     const session = await getSession()
  //     if(!session){
  //       signIn()
  //     }else {
  //       setloading(false)
  //     }
  //   }
  //   securePage()
  // },[])

  // if (loading){
  //   return <h2>Loading...</h2>

  // }


  if (error) return <h1>Something went wrong!</h1>
  if (!data) return ( 
                <Box sx={{ width: '100%' }}>
                 <LinearProgress
               
                 />
              </Box>
                  );


                  
  
  
  
  const SensorLabel = data.filter((item)=> item.name === 'Boiler Top').map((item)=> formatISO9075(new Date (item.date),{ representation: 'time'}));

  const SensorDataBoilerBottom = data.filter((item)=> item.name === 'Boiler Bottom').map((item)=> item.temp)
  const SensorDataBoilerBottomMax = Math.round(Math.max.apply(null, data.filter((item) =>  item.name === 'Boiler Bottom').map((item) => item.temp)))
  const SensorDataBoilerBottomMin =  Math.round(Math.min.apply(null, data.filter((item) =>  item.name === 'Boiler Bottom').map((item) => item.temp)))
  const SensorDataBoilerBottomCurrent=  Math.round(data.filter((item) =>  item.name === 'Boiler Bottom').map((item) => item.temp).slice(-1)[0])

  const SensorDataBoilerTop = data.filter((item)=> item.name === 'Boiler Top').map((item)=> item.temp)
  const SensorDataBoilerTopMax = Math.round(Math.max.apply(null, data.filter((item) =>  item.name === 'Boiler Top').map((item) => item.temp)))
  const SensorDataBoilerTopMin =  Math.round(Math.min.apply(null, data.filter((item) =>  item.name === 'Boiler Top').map((item) => item.temp)))
  const SensorDataBoilerTopCurrent=  Math.round(data.filter((item) =>  item.name === 'Boiler Top').map((item) => item.temp).slice(-1)[0])
  
  const SensorDataCoolerIn = data.filter((item)=> item.name === 'Cooler In').map((item)=> item.temp)
  const SensorDataCoolerInMax = Math.round(Math.max.apply(null, data.filter((item) =>  item.name === 'Cooler In').map((item) => item.temp)))
  const SensorDataCoolerInMin =  Math.round(Math.min.apply(null, data.filter((item) =>  item.name === 'Cooler In').map((item) => item.temp)))
  const SensorDataCoolerInCurrent=  Math.round(data.filter((item) =>  item.name === 'Cooler In').map((item) => item.temp).slice(-1)[0])
  
  const SensorDataCoolerOut = data.filter((item)=> item.name === 'Cooler Out').map((item)=> item.temp)
  const SensorDataCoolerOutMax = Math.round(Math.max.apply(null, data.filter((item) =>  item.name === 'Cooler Out').map((item) => item.temp)))
  const SensorDataCoolerOutMin =  Math.round(Math.min.apply(null, data.filter((item) =>  item.name === 'Cooler Out').map((item) => item.temp)))
  const SensorDataCoolerOutCurrent=  Math.round(data.filter((item) =>  item.name === 'Cooler Out').map((item) => item.temp).slice(-1)[0])

  const handleClick = (event) => {
    setAnchorEl(event.currentTarget);
  };
  const handleClose = (event) => {
    let event_range = event.target.getAttribute("value")
    setTo(TimestampNow)
    setFrom(TimestampNow-(3600*event_range))
    setRange(event_range)
    setAnchorEl(null);
    
  };

  const handleprevious = () => {
   
      setTo(to+(3600*range))
      setFrom(from+(3600*range))
  
      
  };

  const handlenext = () => {
   
    setTo(to-(3600*range))
    setFrom(from-(3600*range))
    
   
};



  const handleExpandClick = () => {
    setExpanded(!expanded);
  };


  
  
  
  return (
    
    <div>
      <Grid  container
        direction="row"
        justifyContent="space-around"
        alignItems="center">
            <Box sx={{ display: 'flex', alignItems: 'center', pl: 1, pb: 1 }}>
          <IconButton aria-label="previous"  onClick={handlenext}>
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
                onClose={handleClose}
                MenuListProps={{
                  'aria-labelledby': 'basic-button',
                }}
              >
                <MenuItem value="1" onClick={handleClose}>Last 1 hour</MenuItem>
                <MenuItem value="3" onClick={handleClose}>Last 3 hours</MenuItem>
                <MenuItem value="6" onClick={handleClose}>Last 6 hours</MenuItem>
                <MenuItem value="12" onClick={handleClose}>Last 12 hours</MenuItem>
                <MenuItem value="24" onClick={handleClose}>Last 1 day</MenuItem>
                <MenuItem value="48" onClick={handleClose}>Last 2 days</MenuItem>
              </Menu>  

              <IconButton aria-label="next"  onClick={handleprevious}>
            {theme.direction === 'rtl' ? <SkipPreviousIcon /> : <SkipNextIcon />}
          </IconButton>
        </Box>
    
      </Grid>
      <Grid  container
         direction="row"
         justifyContent="space-around"
         alignItems="center"
         style={{ gap: 15}}>
      <Box
      sx={{
        bgcolor: 'background.paper',
        boxShadow: 1,
        borderRadius: 1,
        p: 2,
        width: 210 ,
      }}
     
    >
      <Grid  container
        
        justifyContent="space-between"
        alignItems="center">
      <Grid>
      <Box sx={{ color: 'text.secondary' , display: 'inline'}}>Boiler Bottom</Box>
      </Grid>
      <Grid>
      <Box sx={{ color: 'text.primary', fontSize: 34, fontWeight: 'medium' }}>
      {`${SensorDataBoilerBottomCurrent}°C`}
      </Box>
      </Grid>
      </Grid>
      <ExampleChart style='mini'  label ='Boiler Bottom' data={SensorDataBoilerBottom} labels={SensorLabel} options={options_simple} />

      <Box sx={{ color: 'text.secondary', fontSize: 12 }}>
      {`Min: ${SensorDataBoilerBottomMin}°C  Max: ${SensorDataBoilerBottomMax}°C`} 
      </Box>
    </Box>
     
      <Box
      sx={{
        bgcolor: 'background.paper',
        boxShadow: 1,
        borderRadius: 1,
        p: 2,
        width: 210 ,
      }}
     
    >
      <Grid  container
        
        justifyContent="space-between"
        alignItems="center">
      <Grid>
      <Box sx={{ color: 'text.secondary' , display: 'inline'}}>Boiler Top</Box>
      </Grid>
      <Grid>
      <Box sx={{ color: 'text.primary', fontSize: 34, fontWeight: 'medium' }}>
      {`${SensorDataBoilerBottomCurrent}°C`}
      </Box>
      </Grid>
      </Grid>
      <ExampleChart style='mini'  label ='Boiler Bottom' data={SensorDataBoilerBottom} labels={SensorLabel} options={options_simple} />

      <Box sx={{ color: 'text.secondary', fontSize: 12 }}>
      {`Min: ${SensorDataBoilerTopMin}°C  Max: ${SensorDataBoilerTopMax}°C`} 
      </Box>
    </Box>
     
    <Box
      sx={{
        bgcolor: 'background.paper',
        boxShadow: 1,
        borderRadius: 1,
        p: 2,
        width: 210 ,
      }}
     
    >
      <Grid  container
        
        justifyContent="space-between"
        alignItems="center">
      <Grid>
      <Box sx={{ color: 'text.secondary' , display: 'inline'}}>Boiler Top</Box>
      </Grid>
      <Grid>
      <Box sx={{ color: 'text.primary', fontSize: 34, fontWeight: 'medium' }}>
      {`${SensorDataBoilerBottomCurrent}°C`}
      </Box>
      </Grid>
      </Grid>
      <ExampleChart style='mini'  label ='Boiler Bottom' data={SensorDataBoilerBottom} labels={SensorLabel} options={options_simple} />

      <Box sx={{ color: 'text.secondary', fontSize: 12 }}>
      {`Min: ${SensorDataBoilerTopMin}°C  Max: ${SensorDataBoilerTopMax}°C`} 
      </Box>
    </Box>

    <Box
      sx={{
        bgcolor: 'background.paper',
        boxShadow: 1,
        borderRadius: 1,
        p: 2,
        width: 210 ,
      }}
     
    >
      <Grid  container
        
        justifyContent="space-between"
        alignItems="center">
      <Grid>
      <Box sx={{ color: 'text.secondary' , display: 'inline'}}>Boiler Top</Box>
      </Grid>
      <Grid>
      <Box sx={{ color: 'text.primary', fontSize: 34, fontWeight: 'medium' }}>
      {`${SensorDataBoilerBottomCurrent}°C`}
      </Box>
      </Grid>
      </Grid>
      <ExampleChart style='mini'  label ='Boiler Bottom' data={SensorDataBoilerBottom} labels={SensorLabel} options={options_simple} />

      <Box sx={{ color: 'text.secondary', fontSize: 12 }}>
      {`Min: ${SensorDataBoilerTopMin}°C  Max: ${SensorDataBoilerTopMax}°C`} 
      </Box>
    </Box>

    </Grid>
  
      
     
      <p></p>
     
       

      <Grid  container
        //direction="column"
        //columns={{ xs: 4, sm: 8, md: 12 }}
        justifyContent="space-around"
        alignItems="center"
        style={{ gap: 15 }}>
        
        <Grid Grid item xs={10} sm={10} md={5}>
        <Card>
      <CardHeader 
        avatar={
          <Avatar  variant="rounded" style={{color:'#B9E4F5', background:' #72ADC4'}}>
           <DeviceThermostatOutlinedIcon />
        </Avatar>
        }
        
        title={`Boiler Bottom: ${SensorDataBoilerBottomCurrent}°C`}
        subheader={`Min: ${SensorDataBoilerBottomMin}°C  Max: ${SensorDataBoilerBottomMax}°C`} 
      />
      <CardContent>
      <ExampleChart style='normal' label ='Boiler Bottom' data={SensorDataBoilerBottom} labels={SensorLabel} options={options} />
      </CardContent>
      </Card>
      </Grid>
      <Grid Grid item xs={10} sm={10} md={5}>
      <Card>
      <CardHeader 
        avatar={
          <Avatar  variant="rounded" style={{color:'#B9E4F5', background:' #72ADC4'}}>
           <DeviceThermostatOutlinedIcon />
        </Avatar>
        }
        
        title={`Boiler Top: ${SensorDataBoilerTopCurrent}°C`}
        subheader={`Min: ${SensorDataBoilerTopMin}°C  Max: ${SensorDataBoilerTopMax}°C`} 
      />
      <CardContent>
      <ExampleChart style='normal' label ='Boiler Top' data={SensorDataBoilerTop} labels={SensorLabel} options={options} />
      </CardContent>
      </Card>
      </Grid>
      <Grid Grid item xs={10} sm={10} md={5}>
      <Card>
      <CardHeader 
        avatar={
          <Avatar  variant="rounded" style={{color:'#B9E4F5', background:' #72ADC4'}}>
           <DeviceThermostatOutlinedIcon/>
        </Avatar>
        }
      
        title={`Cooler In: ${SensorDataCoolerInCurrent}°C`}
        subheader={`Min: ${SensorDataCoolerInMin}°C  Max: ${SensorDataCoolerInMax}°C`} 
      />
      <CardContent>
      <ExampleChart  style='normal' label ='Cooler In' data={SensorDataCoolerIn} labels={SensorLabel} options={options} />
      </CardContent>
      </Card>
      </Grid>
      <Grid Grid item xs={10} sm={10} md={5}>
      <Card >
      <CardHeader 
        avatar={
          <Avatar  variant="rounded" style={{color:'#B9E4F5', background:' #72ADC4'}}>
           <DeviceThermostatOutlinedIcon />
        </Avatar>
        }
      
        title={`Cooler Out: ${SensorDataCoolerOutCurrent}°C`} 
        subheader={`Min: ${SensorDataCoolerOutMin}°C  Max: ${SensorDataCoolerOutMax}°C`} 
      />
      <CardContent>
      <ExampleChart  style='normal' label ='Cooler Out' data={SensorDataCoolerOut} labels={SensorLabel} options={options} />
      </CardContent>
      </Card>
      </Grid>
      </Grid>
     
    </div>
  );
}
