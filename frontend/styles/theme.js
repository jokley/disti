import { createTheme, responsiveFontSizes } from "@mui/material/styles";
import { deepPurple, amber } from "@mui/material/colors";

// Create a theme instance.
let theme = createTheme({
    palette: {
      primary: {
        main: '#143968',
      },
      secondary: {
        main: '#4a4a49',
      },
    },
  })

theme = responsiveFontSizes(theme);

export default theme;
