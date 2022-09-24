import React from 'react'
import {Dialog, DialogContent, DialogTitle, makeStyles, Typography} from '@mui/material';
import Controls from './Controls';
import CloseIcon from '@mui/icons-material/Close';


// // const useStyles = makeStyles(theme =>({
//     dialogWrapper : {
//         padding : theme.spacing(2),
//         position: 'absolute',
//         top: theme.spacing(5)
//     },
//     DialogTitle:{
//         paddingRight: '0px'
//     }
// }))

export default function Popup(props) {

    const {title, children, openPopup, setOpenPopup,setRefresh} = props;
    // const classes = useStyles();

    return (
       <Dialog open={openPopup} maxWidth="md" >
           <DialogTitle >
               <div style ={{display: 'flex'}}>
                   <Typography variant="h6" component="div" style={{flexGrow:1}}> 
                       {title}
                   </Typography>
                   <Controls.ActionButton
                        color= "secondary"
                        onClick={()=>{setOpenPopup(false),setRefresh(true)}} >   
                   <CloseIcon />
                   </Controls.ActionButton>
               </div>
           </DialogTitle>
           <DialogContent dividers>
               {children}
           </DialogContent>

       </Dialog>
    )
}
