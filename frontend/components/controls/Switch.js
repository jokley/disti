import * as React from 'react';
import Switch from '@mui/material/Switch';
import FormControlLabel from '@mui/material/FormControlLabel';
import { Box } from '@mui/system';

export default function ControlledSwitch(props) {

const {label, onChange,checked, key} = props;


  return (
    <FormControlLabel 
    sx={{ marginTop:-1 ,marginBottom:-0.5 }}
    labelPlacement="top"
    control={
    <Switch 
      sx={{border: '1px solid #ced4da', borderRadius: 1 }}
      key={key}
      checked={checked}
      onChange={onChange}
      inputProps={{ 'aria-label': 'controlled' }}
      />} label={
        <Box component="div" fontSize={12} color='grey.600' >
        {label}
      </Box>  
        } />
  );
}