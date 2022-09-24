import React from 'react'
import { Button as MuiButton} from '@mui/material';
//import { styled } from '@mui/material/styles';



// const MuiButton= styled(StyledButton)`
//     root:{
//         margin:theme.spacing(0.5)
//     },
//     label:{
//         textTransform:'none'
//     }
// `;



export default function Button(props) {

    const {text,size, color, variant,onClick, ...other} = props
    return (
     <MuiButton
     variant={variant || "contained"}
     size={size|| "small"}
     color={color|| "primary"}
     onClick={onClick}
     {...other}>
         {text}
     </MuiButton>
    )
}
