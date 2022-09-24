import React from 'react'
import { FormControl, FormHelperText, InputLabel,MenuItem,Select as MuiSelect } from '@mui/material';
import { styled } from '@mui/material/styles';
//import InputBase from '@mui/material/InputBase';



const WKSelect= styled(MuiSelect)`

   

`;


export default function Select(props) {

    const {name, label, value, error=null, onChange, options} = props;
    
    return (
  
        <FormControl  sx={{ m: 0.5, marginTop: 2.4 }} 
        size="small"
        {...(error && {error:true})}>
            <InputLabel>{label}</InputLabel>
            <WKSelect
           
            SelectDisplayProps={{ style: {width: 80 } }}
            MenuProps={{
                PaperProps: {
                  sx: {
                    "& .MuiMenuItem-root.Mui-selected": {
                      backgroundColor: "lightblue"
                    },
                    "& .MuiMenuItem-root:hover": {
                      backgroundColor: "lightgrey"
                    },
                    "& .MuiMenuItem-root.Mui-selected:hover": {
                      backgroundColor: "#2FD5B4"
                    }
                  }
                }
              }}
            label = {label}
            name = {name}
            value ={value}
            multiple={true}
            onChange={onChange}>
                  <MenuItem value="All">All</MenuItem>  
                {
                     options.map(
                        item =>(<MenuItem key={item.id} value={item.id}>{item.title}</MenuItem>)
                    ) 

              
                }
                

            </WKSelect>
            {error && <FormHelperText>{error}</FormHelperText>}
            
        </FormControl>
    )
}
