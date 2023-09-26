import Head from 'next/head'
import Image from 'next/image'
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import Paper from '@mui/material/Paper';
import useSWR from 'swr'
import IconButton from '@mui/material/IconButton';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import ModeEditOutlineOutlinedIcon from '@mui/icons-material/ModeEditOutlineOutlined';




export default function Home() {
  
 

  const addCar = async event => {
    event.preventDefault()

    const res = await fetch('https://disti.pi.jokley.at/backend/cars', {
      body: JSON.stringify({
        name: event.target.name.value,
        model:event.target.model.value,
        doors: event.target.doors.value,

      }),
      headers: {
        'Content-Type': 'application/json'
      },
      method: 'POST'
    })
 
    const result = await res.json() 
    console.log(result)
    mutate(data)
  }

  const editCar = async event => {
    event.preventDefault()

    const carId = event.currentTarget.value

    

    const res = await fetch(`https://disti.pi.jokley.at/backend/cars/${carId}`, {
      body: JSON.stringify({
        name: 'test_name',
        model:'test_model',
        doors: '11',

      }),
      headers: {
        'Content-Type': 'application/json'
      },
      method: 'PUT'
    })
 
    const result = await res.json() 
    console.log(result)
    mutate(data)
  }

  const deleteCar = async event => {
    event.preventDefault()

    const carId = event.currentTarget.value

    const res = await fetch(`https://disti.pi.jokley.at/backend/cars/${carId}`, {
      // body: JSON.stringify({
      //   name: event.target.name.value,
      //   model:event.target.model.value,
      //   doors: event.target.doors.value,

      // }),
      // headers: {
      //   'Content-Type': 'application/json'
      // },
      method: 'DELETE'
    })
 
    const result = await res.json() 
    console.log(result)
    mutate(data)
    
  }

  const url = (`https://disti.pi.jokley.at/backend/cars`);

  const { data, error, mutate } = useSWR(url,{refreshInterval: 1000});

  if (error) return <h1>Something went wrong!</h1>
  if (!data) return  <h1>Loading...</h1>
 
                


  return (
    <>
    <Paper  sx={{paddingBottom:1,paddingTop:3}}>
    <form onSubmit={addCar}>
      <label htmlFor="name">Name</label>
      <input id="name" name="name" type="text" autoComplete="name" required />
      <label htmlFor="model">Model</label>
      <input id="model" name="model" type="text" autoComplete="model" required />
      <label htmlFor="doors">Doors</label>
      <input id="doors" name="doors" type="text" autoComplete="doors" required />
      <button type="submit">add</button>
    </form>
    </Paper>
    <p></p>

      <TableContainer component={Paper}>
      <Table sx={{ minWidth: 650 }} aria-label="simple table">
        <TableHead>
          <TableRow>
            <TableCell>Marke</TableCell>
            <TableCell align="right">Model</TableCell>
            <TableCell align="right">Doors</TableCell>
            <TableCell align="right">Edit</TableCell>
            <TableCell align="right">Delte</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {data.map((row) => (
            <TableRow
              key={row.id}
              sx={{ '&:last-child td, &:last-child th': { border: 0 } }}
            >
              <TableCell component="th" scope="row">
                {row.name}
              </TableCell>
              <TableCell align="right">{row.model}</TableCell>
              <TableCell align="right">{row.doors}</TableCell>
              <TableCell align="right">
              <IconButton
               value={row.id}
               onClick={editCar}
              >
              <ModeEditOutlineOutlinedIcon />
              </IconButton> 
              </TableCell>
              <TableCell align="right">
              <IconButton
               value={row.id}
               onClick={deleteCar}
              >
              <DeleteOutlineIcon />
              </IconButton> 
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  

   
      </>
  )
}
