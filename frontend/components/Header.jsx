import AppBar from "@mui/material/AppBar";
import Container from "@mui/material/Container";
import Toolbar from "@mui/material/Toolbar";
import { styled } from '@mui/material/styles';
import IconButton from "@mui/material/IconButton"
import Home from "@mui/icons-material/Home"
import MuiNextLink from "@components/MuiNextLink";
import Navbar from './Navbar';
import SideDrawer from "./SideDrawer";
import HideOnScroll from "./HideOnScroll";
import Fab from "@mui/material/Fab";
import KeyboardArrowUp from "@mui/icons-material/KeyboardArrowUp";
import BackToTop from "./BackToTop";
import { Avatar, Paper } from "@mui/material";
import Image from 'next/image'



const Offset = styled("div")(({ theme }) => theme.mixins.toolbar);

const StyledAppBar = styled(AppBar)`
  background-image:  linear-gradient(45deg, #368CC6 30%, #143968 90%);
`;



export const navLinks = [
    //{ title: `home`, path: `/` },
    { title: `menu`, path: `/menu` },
    { title: `contact`, path: `/contact` },
    { title: `dashboard`, path: `/dashboard` },
  ];


  

const Header = () => {

 
  return (
    <>
    <HideOnScroll>
      <StyledAppBar position="fixed" height="5px">
      
        <Toolbar>
      
          <Container
            maxWidth="false"
            sx={{ display: `flex`}}
          >

            <SideDrawer navLinks={navLinks} />
            <IconButton  aria-label="home" sx={{paddingLeft: 3}}>
                <MuiNextLink activeClassName="active" href="/"  >
               
                  <Image src="/logo.png" alt="me" width="30" height="50" /> 
                 
                </MuiNextLink>
            </IconButton>
          
            <Navbar navLinks={navLinks}/>
           
          </Container>
         

            <IconButton
            // onClick={(e)=> {
            //   e.preventDefault()
            //   signOut()

            //     }}   
          >
            <MuiNextLink activeClassName="active" href="/"  >
            <Avatar sx={{ bgcolor: 'orange'}}></Avatar>
          </MuiNextLink>
           
           </IconButton>
       
         
        </Toolbar>
      </StyledAppBar>
    </HideOnScroll>
      <Offset id="back-to-top-anchor" />
      <BackToTop>
        <Fab color="secondary" size="large" aria-label="back to top">
            <KeyboardArrowUp />
        </Fab>
     </BackToTop>
    </>
  );
};

export default Header;
