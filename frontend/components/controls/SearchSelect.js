import React, { useState, useMemo } from "react";
import {
  Box,
  FormControl,
  Select,
  MenuItem,
  InputLabel,
  ListSubheader,
  TextField,
  InputAdornment,
  Checkbox,
  ListItemIcon,
} from "@mui/material";
import SearchIcon from "@mui/icons-material/Search";

const containsText = (text, searchText) =>
    text.toString().toLowerCase().indexOf(searchText.toString().toLowerCase()) > -1;
    
const allOptions = ["Option One", "Option Two", "Option Three", "Option Four"];

export default function Searchselect(props) {

  const {name, label, value, error=null, onChange, options, multiple,disabled,searchText,setSearchText} = props;
  
  // const [selectedOption, setSelectedOption] = useState(options);

  // const [searchText, setSearchText] = useState('');
  const displayedOptions = useMemo(
    () => options.filter((option) => containsText(option.title ? option.title : '', searchText ? searchText :'')),
    [searchText,options]
  );

  const isAllSelected = options.length > 0 && value.length === options.length;



  // console.log('Options')
  // console.log(options)
  // console.log('DisplayedOptions')
  // console.log(displayedOptions)

  return (
    <Box sx={{ m: 0.5 }}>
      <FormControl sx={{ m: 0.5, marginTop: 2.4 }} 
        size="small" 
        {...(error && {error:true})}>
        <InputLabel>{label}</InputLabel>
        <Select
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
              },
              
            }}
         
          // Disables auto focus on MenuItems and allows TextField to be in focus
          // MenuProps={{ autoFocus: false }}
          labelId="search-select-label"
          id="search-select"
          disabled ={disabled}
          value={value}
          label={label}
          multiple={multiple}
          onChange={onChange}
          // onClose={() => setSearchText("")}
          // This prevents rendering empty string in Select's value
          // if search text would exclude currently selected option.
          renderValue={(options) => options.join(", ") }
        >
          {/* TextField is put into ListSubheader so that it doesn't
              act as a selectable item in the menu
              i.e. we can click the TextField without triggering any selection.*/}
          <ListSubheader>
            <TextField
              
              size="small"
              // Autofocus on textfield
              value={searchText}
              autoFocus
              placeholder="Type to search..."
              fullWidth
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <SearchIcon />
                  </InputAdornment>
                )
              }}
              onChange={(e) => setSearchText(e.target.value)}
              // onChange={onChangeSearchText}
              onKeyDown={(e) => {
                if (e.key !== "Escape") {
                  // Prevents autoselecting item while typing (default Select behaviour)
                  e.stopPropagation();
                }
                if (e.key !== "Enter") {
                  // Prevents autoselecting item while typing (default Select behaviour)
                  e.stopPropagation();
                }
              }}
            />
          </ListSubheader>
         <MenuItem value={"All"}
                    sx={{fontWeight: 500}}>
          <ListItemIcon>
            <Checkbox
              checked={isAllSelected}
              indeterminate={value.length > 0 && value.length < options.length}
            />
          </ListItemIcon>
           {isAllSelected ? 'Deselect All': 'Select All'} </MenuItem>  
           {displayedOptions.map((option, i) => (
            <MenuItem key={option.id} value={option.id}>
              <Checkbox checked={value.indexOf(option.id) > -1} />
              {option.title}
            </MenuItem>
          ))}
        </Select>
      </FormControl>
    </Box>
  );
}
