import React,{useState} from 'react'
//import {makeStyles} from '@mui/material';


export function useFrom(initialFValues, validateOnChange=false,validate) {

    const [values,setvalues] = useState(initialFValues);
    const [errors,setErrors] = useState({});

    
    const handleInputChange = e=>{
        const {name,value} = e.target
        setvalues({
            ...values,
            [name]:value
        })
        if(validateOnChange)
        validate({[name]:value})
    }

    const resetForm = () =>{
        setvalues(initialFValues);
        setErrors({})
    
    }

    return {
       values,
       setvalues,
       errors,
       setErrors,
       handleInputChange,
       resetForm
    }
}

// const useStyles = makeStyles(theme => ({
//     root:{
//          '& .MuiFormControl-root':{
//              width:'80%',
//              margin: theme.spacing(1)
//          }
//     }
// }))



export function Form(props) {
    
    //const classes = useStyles();
    const {children,...other} = props;
    return (
        <form autoComplete="off" {...other}>
            {props.children}
        </form>
    )
}
