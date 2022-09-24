import React, { useState } from 'react';
import { SketchPicker  } from 'react-color';
import {Button, Dialog, DialogActions, DialogContent, DialogTitle, makeStyles, Typography} from '@mui/material';
import Controls from './Controls';
import CloseIcon from '@mui/icons-material/Close';

const popover = {
    position: 'absolute',
    zIndex: '2', 
  };
  const cover = {
    position: 'fixed',
    top: '0px',
    right: '0px',
    bottom: '0px',
    left: '0px',
  };



export default function ColorPicker(props) {

const {color, setColor, onChange, openPopupColor, setOpenPopupColor,onSubmit,setRefresh} = props;
 

  return (
     
    <Dialog open={openPopupColor} maxWidth="md" >
        <DialogTitle >
            <div style ={{display: 'flex'}}>
                <Typography variant="h6" component="div" style={{flexGrow:1}}> 
                    Color Picker
                </Typography>
                <Controls.ActionButton
                     color= "secondary"
                     onClick={()=>{setOpenPopupColor(false),setRefresh(true)}} >   
                <CloseIcon />
                </Controls.ActionButton>
            </div>
        </DialogTitle>
        <DialogContent dividers>
        <SketchPicker 
          color={color}
          onChange={onChange}
          />
          <DialogActions>
            <Button onClick={()=>{setOpenPopupColor(false),setRefresh(true)}}>Abbrechen</Button>
            <Button onClick={()=>{setOpenPopupColor(false),onSubmit()}} autoFocus>Ok</Button>
          </DialogActions>
        </DialogContent>
        
       

    </Dialog>

 )

/*     return (
      <div>
        <button onClick={handleClick }>Pick Color</button>
        { visible ? <div style={ popover }>
          <div style={ cover } onClick={handleClose }/>
          <SketchPicker 
          color={color}
          onChange={handleChange}
          />
        </div> : null }
      </div>
    ) */
  }

