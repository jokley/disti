import { FormControl, FormControlLabel, FormLabel,Radio,RadioGroup as MuiRadioGroup } from '@mui/material';
import { Box } from '@mui/system';
import React from 'react'

export default function RadioGroup(props) {

    const  {name,label,value, onChange,items} = props;
    return (
        <FormControl>
        <FormLabel sx={{ marginTop: -0.8, paddingLeft: 0.2 }} >
        <Box component="div" fontSize={12} color='grey.600'  >
        {label}
      </Box>  
        </FormLabel>
        <MuiRadioGroup row
            name={name}
            value={value}
            onChange={onChange}
            sx={{paddingLeft:1 ,marginTop:-0.3, border: '1px solid #ced4da', borderRadius: 1,  '& .MuiSvgIcon-root': {
                fontSize: 20,
              },}}>

                {

                    items.map(
                        (item)=>(
                            <FormControlLabel key={item.id} value ={item.id} control={<Radio/>} label={item.title} />  
                        )
                    )

                }
        </MuiRadioGroup>
    </FormControl>
    )
}

