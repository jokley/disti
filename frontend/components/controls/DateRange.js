import * as React from "react";
import TextField from "@mui/material/TextField";
import { AdapterMoment } from '@mui/x-date-pickers/AdapterMoment';
import {LocalizationProvider} from "@mui/x-date-pickers/LocalizationProvider";
import {DatePicker} from "@mui/x-date-pickers/DatePicker";
import { DateTimePicker } from '@mui/x-date-pickers/DateTimePicker';

import moment from 'moment'

export default function BasicTimeRangePicker(props) {

  const {from,to,onChangeFrom,onChangeTo} = props;
  
  // const [from, setFrom] = React.useState(new Date(moment.unix(von).startOf('year')));
  // const [to, setTo] = React.useState(new Date(moment.unix(bis).endOf('year')));


  return (
    <LocalizationProvider dateAdapter={AdapterMoment}>
      <DateTimePicker
        // views={["day","month", "year"]}
        label="Von"
        minDate={new Date(moment().startOf('year').add(-20,'year'))}
        maxDate={new Date(moment().startOf('year').add(30,'year'))}
        value={moment.unix(from)}
        onChange={onChangeFrom}
        renderInput={(params) => (
          <TextField sx={{ m: 2 }} {...params} helperText={null}  size="small"/>
        )}
      />
      <DateTimePicker
        // views={["day","month", "year"]}
        label="Bis"
        minDate={new Date(moment().startOf('year').add(-20,'year'))}
        maxDate={new Date(moment().startOf('year').add(30,'year'))}
        value={moment.unix(to)}
        onChange={onChangeTo}
        renderInput={(params) => (
          <TextField sx={{ m: 2 }} {...params} helperText={null} size="small"/>
        )}
      />
    </LocalizationProvider>
  );
}
