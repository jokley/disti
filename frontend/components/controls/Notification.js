import Snackbar from '@mui/material/Snackbar';
import Alert from '@mui/material/Alert';
import React from 'react'
//import { useRouter } from 'next/router'



// const useStyles = makeStyles(theme =>({
//     root:{
//         top:theme.spacing(9)
//     }
// }))

export default function Notification(props) {

    const {notify, setNotify} = props;
    //const router = useRouter()
    //const classes = useStyles()

    const handleClose = (event,reason) => {
        if (reason === 'clickaway'){
            return;
        }
        setNotify({
            ...notify,
            isOpen : false
        })
    }

    return (
        
        <Snackbar
        //className = {classes.root}
        open={notify.isOpen}
        autoHideDuration = {2000}
        anchorOrigin={{vertical:'top',horizontal:'center'}}
        onClose={handleClose}>
         <Alert 
         severity={notify.type}
         onClose={handleClose}>
            {notify.message}
         </Alert>
        </Snackbar>
        
    )
}
