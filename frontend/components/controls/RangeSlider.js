import * as React from 'react';
import Box from '@mui/material/Box';
import Slider from '@mui/material/Slider';
import { Stack, Typography } from '@mui/material';

function valuetext(value) {
  return `${value}°C`;
}

export default function RangeSlider(props) {
   
  const {name,label,value, min, max, step, onChange, ...other} = props;
 
  return (
    
    <Box sx={{ width: 200, paddingTop:0.4 , paddingLeft:2 }}>
      <Stack 
      direction="row" 
      justifyContent="space-between">
      <Typography sx={{fontSize:12, color:'grey.600'}}>
          {'> ' + Intl.NumberFormat("de-DE",{ maximumFractionDigits: 0}).format(value[0]/1000000)+' Mio €'}
      </Typography>
    
      <Typography sx={{fontSize:12, color:'grey.600'}}>
          {'< ' + Intl.NumberFormat("de-DE",{ maximumFractionDigits: 0}).format(value[1]/1000000)+' Mio €'}
      </Typography>

      </Stack>
     
    <Slider sx={{border: '1px solid #ced4da', borderRadius: 1 ,height:9}}
      size="small"
      aria-label="Small"
      getAriaLabel={() => 'Temperature range'}
      value={value}
      onChange={onChange}
      valueLabelDisplay='auto'
      valueLabelFormat={value => <div>{Intl.NumberFormat("de-DE",{style:"currency", currency:"EUR", maximumFractionDigits: 0}).format(value)}</div>}
      getAriaValueText={valuetext}
      min={min}
      max={max}
      step={step}
    />
  </Box>
  )
}
