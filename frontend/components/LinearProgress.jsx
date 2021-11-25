import React from 'react'
import { LinearProgress as MuiLinearProgress} from '@mui/material';

export default function LinearProgress(props) {

    const {backgroundColor} = props
    return (
        <div>
     <MuiLinearProgress sx={{marginTop: 1.1,height: 5,  backgroundColor: {backgroundColor},}} />
     </div>
    )
}
