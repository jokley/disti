import { Avatar, Card, CardContent, CardHeader, Divider, fabClasses, Grid, IconButton, LinearProgress, makeStyles, Menu, MenuItem, Stack} from "@mui/material";
import { useTheme } from '@mui/material/styles';
import DeviceThermostatOutlinedIcon from '@mui/icons-material/DeviceThermostatOutlined';
import EuroIcon from '@mui/icons-material/Euro';
import DateRangeOutlinedIcon from '@mui/icons-material/DateRangeOutlined';
import SkipPreviousIcon from '@mui/icons-material/SkipPrevious';
import SkipNextIcon from '@mui/icons-material/SkipNext';
import EngineeringSharpIcon from '@mui/icons-material/EngineeringSharp';
import AddShoppingCartSharpIcon from '@mui/icons-material/AddShoppingCartSharp';
import ProductionQuantityLimitsIcon from '@mui/icons-material/ProductionQuantityLimits';
import ShoppingCartCheckoutIcon from '@mui/icons-material/ShoppingCartCheckout';
import ShoppingCartOutlinedIcon from '@mui/icons-material/ShoppingCartOutlined';
import CreditScoreIcon from '@mui/icons-material/CreditScore';
import CreditCardIcon from '@mui/icons-material/CreditCard';
import React, { useEffect, useState, useContext } from "react";
import MixedChart from "../components/charts/MixedChart";
import SinglePiChart from "../components/charts/SinglePiChart";
import PiChart from "../components/charts/PiChart"
import BarChart from "../components/charts/BarChart"
import Doughnut from "../components/charts/DoughnutChart"
import Gauge from "../components/charts/GaugeChart"
import StackedDoughnut from "../components/charts/StackedDoughnutChart"
import {options, options_simple} from "../components/ChartOptions"
import useSWR from 'swr'
import { Box } from "@mui/system";
import moment from 'moment'
//import { formatISO9075 } from "date-fns";
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import { CardActions, Collapse } from "@mui/material";
import { styled } from '@mui/material/styles';
import Controls from '../components/controls/Controls'; 
import { MinimizeSharp, ResetTvRounded, SummarizeSharp } from "@mui/icons-material";
import TrendingDownIcon from '@mui/icons-material/TrendingDown';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import UserContext from '../context/userContext';
import MUITable from '../components/Table'
import { useRouter } from "next/router"



const colorSP = 'rgba(81, 250, 145,0.5)';
const colorGP = 'rgba(20, 120, 175, 0.5)';
const colorOP = 'rgba(250, 186, 81, 0.5)';
const colorKP = 'rgba(89, 77, 167, 0.5)';
const colorMin = 'rgba(0,255,100, 0.5)';
const colorMax = 'rgba(255,50,100, 0.5)';
const white = 'rgba(255,255,255, 0.5)';





/* const useStyles = makeStyles({
  root: {
    background: 'linear-gradient(45deg, #B9E4F5 30%, #72ADC4 90%)',
    border: 0,
    borderRadius: 3,
    boxShadow: '0 3px 5px 2px rgba(50, 105, 135, .3)',
    color: 'black',
    padding: '3 30px',
  },
  colorPrimary: {
    backgroundColor: '#E9E9E9'
  },
  bar: {
    borderRadius: 5,
    backgroundColor: '#72ADC4'
  }
  
}); */

const color00 = 'rgba(0, 153, 153,1)';
const color01 = 'rgba(0, 204, 204, 1)';
const color02 = 'rgba(0, 255, 255, 1)';
const color03 = 'rgba(153, 255, 255, 1)';
const color04 = 'rgba(102, 204, 255, 1)';
const color05= 'rgba(102, 153, 204, 1)';
const color06 = 'rgba(0, 176, 191  , 1)';
const color07 = 'rgba(204, 102, 153,1)';

const genderItems = [
  {id:'0',title:'Mitarbeiter'},
  {id:'1',title:'Team'},
  {id:'2',title:'Projektleiter'},
  {id:'3',title:'Anlagen'},
  {id:'4',title:'Controller'},
]





export default function App() {

  const [loading, setloading] = useState(true)

  



  
  const TimestampNow = Math.round(new Date().getTime()/1000);
  


  //const classes = useStyles();
  const theme = useTheme();

  const { user } = useContext(UserContext);
  
  const [from, setFrom] = useState(moment().startOf('year').add(-5,'year').unix());
  const [to,setTo] = useState(moment().startOf('year').add(10,'year').unix());
  const [range, setRange] = useState(1);
  const [anchorEl, setAnchorEl] = useState(null);
  const open = Boolean(anchorEl);

  const [paketItems,setPaketItems]= useState([]);
  const [vorhabenItems,setVorhabenItems]= useState([]);
  const [mitarbeiterItems,setmitarbeiterItems]= useState([]);
  const [currentMitarbeiterItems,setCurrentMitarbeiterItems]= useState([]);
  const [paketSelect,setPaketSelect] = useState([]);
  const [vorhabenSelect,setVorhabenSelect] = useState([]);
  const [mitarbeiterSelect,setMitarbeiterSelect] = useState([]);
  const [currentMitarbeiterSelect,setCurrentMitarbeiterSelect] = useState([]);

  const router = useRouter();

 

   
  const [queryVID,setQueryVID] = useState([])
 
  const [currentUser,setCurrentUser] = useState(user.ABBREVATION);
  const [currentTeam,setCurrentTeam] = useState(user.TEAM);
  const [groupView,setGroupView] = useState('0');
  const [sqlOption,setSqlOption] = useState('0');
  const [timeStart,setTimeStart] = useState(moment().startOf("year").add(-5,'year').unix());
  const [timeEnd,setTimeEnd] = useState(moment().startOf("year").add(10,'year').unix());

  const[labels,setLabels] = useState([]);
  const[chart00, setchart00] = useState([]);
  const[chart01, setChart01] = useState([]);
  const[chart02, setChart02] = useState([]);
  const[chart03, setChart03] = useState([]);
  const[chart04, setChart04] = useState([]);
  const[chart05, setChart05] = useState([]);
  const[chart06, setChart06] = useState([]);
  const[chart07, setChart07] = useState([]);
  const[chartMax, setChartMax] = useState([]);
  
  const[ist,setIst]=useState([]);
  const[erwartung,setErwartung]=useState([]);
  const[budget,setBudget]=useState([]);
  const[verfügt,setVerfügt]=useState([]);


  const[sumSP, setSumSP] = useState([]);
  const[przSP, setPrzSP] = useState([]);
  const[sumEL, setSumEL] = useState([]);
  const[sumFL, setSumFL] = useState([]);
  
  const[sumGP, setSumGP] = useState([]);
  const[przGP, setPrzGP] = useState([]);
  
  
  const[sumPSP00, setsumPSP00] = useState([]);
  const[sumPSP01, setsumPSP01] = useState([]);
  const[sumPSP02, setsumPSP02] = useState([]);
  const[sumPSP03, setsumPSP03] = useState([]);
  const[sumPSP04, setsumPSP04] = useState([]);
  const[sumPSP05, setsumPSP05] = useState([]);
  const[sumPSP06, setsumPSP06] = useState([]);
  const[sumPSP07, setsumPSP07] = useState([]);
  
  const[sumOP, setSumOP] = useState([]);
  const[przOP, setPrzOP] = useState([]);
  const[sumOPMin, setSumOPMin] = useState([]);
  const[sumOPMax, setSumOPMax] = useState([]);
 
  const[sumKP, setSumKP] = useState([]);
  const[przKP, setPrzKP] = useState([]);
  const[sumKPMin, setSumKPMin] = useState([]);
  const[sumKPMax, setSumKPMax] = useState([]);


  const [checked, setChecked] = useState(false);

  const [paketArt,setPaketArt] = useState([]);
  const [progress, setProgress] = useState(0);

  const [searchTextPaket, setSearchTextPaket] = useState('');
  const [searchTextVorhaben, setSearchTextVorhaben] = useState('');
  const [searchTextCurrentMitarbeiter, setSearchTextCurrentMitarbeiter] = useState('');
  


 
  
  // const url = (`http://localhost:5000/CREAM/Budgetauswertung?VID=4426&VID=4661&VID=8941&VID=7958&VID=7959&VID=8915`);
  // const url = (`http://localhost:5000/CREAM/Budgetauswertung?VID=10216&VID=10217`);
  // const url = (`http://localhost:5000/CREAM/Budgetauswertung?VID=${queryVID}&OPTION=${sqlOption}&TIMERANGE=${checked ? 0 : 1}&USER=${currentUser}&TEAM=${currentTeam}&from=${timeStart}&to=${timeEnd}`);
  // const url_ma = (`http://localhost:5000/CREAM/Sachbearbeiter`)
  // const url = (`https://cream-api.apps.test.egv.at/CREAM/Budgetauswertung?OPTION=${sqlOption}&USER=${currentUser}&TEAM=${currentTeam}&from=${timeStart}&to=${timeEnd}`);
  // const url_ma = (`https://cream-api.apps.test.egv.at/CREAM/Sachbearbeiter`)
  const url = (`${process.env.NEXT_PUBLIC_BACKEND_URL}/CREAM/Budgetauswertung?VID=${queryVID}&OPTION=${sqlOption}&USER=${currentUser}&TEAM=${currentTeam}&from=${timeStart}&to=${timeEnd}`);
  const url_ma = (`${process.env.NEXT_PUBLIC_BACKEND_URL}/CREAM/Sachbearbeiter`)


  const { data, error } = useSWR(url);
  const { data: maData, error: maError } = useSWR(url_ma);

  useEffect(() => {
 
    let vIDQuery;

    if (Array.isArray(router.query["VID"])) {

      for (var i = 0; i < router.query["VID"].length; i++){
        if (i == 0)
          vIDQuery = router.query["VID"][i]
        else
          vIDQuery += '&VID='+router.query["VID"][i]   
      } 
      setQueryVID(vIDQuery)
      
    }
    else{

      setQueryVID(router.query["VID"])

    }
    

  }, [router.query["VID"]])
  

  
  useEffect(() => { 
 
    if (data){

      
    let dataFilter = [];
    let dataFilter_CUM = [];

    dataFilter = data;
    dataFilter_CUM = data;

    


    // let paketeSelect_items = []; 
    // let pakete = [...new Set(data.map(q => q.PAKET))];
    // let pakete_text = [...new Set(data.map(q => q.PROJEKT_BUDGETZUORDNUNG))];
    // for (var i = 0; i < pakete.length; i++) {
    //   paketeSelect_items.push({
    //     id: pakete[i],
    //     title: pakete_text[i],

    //   });
    // }

    // setPaketItems(paketeSelect_items)

    

    let uniqPaket = data.filter(({PAKET}, index, a) => a.findIndex(e => PAKET === e.PAKET) === index);
    
    setPaketItems(
      uniqPaket.map(item =>
        item.PAKET !== 0
        ?
        {
              id: item.PAKET,
              title: item.PROJEKT_BUDGETZUORDNUNG + ' -- ' + item.PAKET + ' -- ' + item.VERANTWORTLICHER,    
        }
        : item
        ));
      

    
    if (!paketSelect.length)
    {
      dataFilter = data;
    }
    else
    {

     dataFilter = data.filter(item =>  paketSelect.includes(item.PAKET));
    }

    
    
    // let vorhabenSelect_items = [];                  
    // let vorhaben = [...new Set(dataFilter.map(q => q.VORHABEN_ID))];
    // let vorhaben_text = [...new Set(dataFilter.map(q => q.BEZEICHNUNG))];
    // for (var i = 0; i < vorhaben.length; i++) {
    //   vorhabenSelect_items.push({
    //     id: vorhaben[i],
    //     title: vorhaben_text[i],
    //   });
    // }

    let uniqVorhaben = dataFilter.filter(({VORHABEN_ID}, index, a) => a.findIndex(e => VORHABEN_ID === e.VORHABEN_ID) === index);
    
    setVorhabenItems(
      uniqVorhaben.map(item =>
        item.VORHABEN_ID !== 0
        ?
        {
              id: item.VORHABEN_ID,
              title: item.BEZEICHNUNG + ' -- ' + item.VORHABEN_ID + ' -- ' + item.VERANTWORTLICHER ,    
        }
        : item
        ));


    if (!vorhabenSelect.length)
    {
      dataFilter = dataFilter;
    }
    else
    {

     dataFilter = dataFilter.filter(item =>  vorhabenSelect.includes(item.VORHABEN_ID));
    }

    // let gantt_werk = []; 
    // let werk = [...new Set(dataFilter.map(q => q.Mitarbeiter_KURZBEZ))];
    // for (var i = 0; i < werk.length; i++) {
    //   gantt_werk.push({
    //     id: werk[i].toString(),
    //     title: werk[i],

    //   });
    // }

    // let uniqMitarbeiter = dataFilter.filter(({VERANTWORTLICHER}, index, a) => a.findIndex(e => VERANTWORTLICHER === e.VERANTWORTLICHER) === index);
    
    // setmitarbeiterItems(
    //   uniqMitarbeiter.map(item =>
    //     item.VERANTWORTLICHER !== 0
    //     ?
    //     {
    //           id: item.VERANTWORTLICHER,
    //           title: item.VERANTWORTLICHER,    
    //     }
    //     : item
    //     ));

   
    // if (!mitarbeiterSelect.length)
    // {
    //   dataFilter = dataFilter;
    // }
    // else
    // {
    //  dataFilter = dataFilter.filter(item => mitarbeiterSelect.includes(String(item.VERANTWORTLICHER)));
    // }



    // dataFilter = dataFilter.filter(item => 
    //   (moment(item.DATE_RANGE) >=timeStart && moment(item.DATE_RANGE) <= timeEnd) ||
    //   (moment(item.DATE_RANGE) <=timeStart && moment(item.DATE_RANGE) >= timeEnd) ||
    //   (moment(item.DATE_RANGE) <= timeEnd && moment(item.DATE_RANGE) >= timeEnd) ||
    //   (moment(item.DATE_RANGE) <=timeStart && moment(item.DATE_RANGE) >=timeStart)) 
    
    

    let monthsLabels = [...new Set(dataFilter.map(item => item.DATE_RANGE))];
    



    let dataChart00 = []; 
    let dataChart01 = [];
    let dataChart02 = [];
    let dataChart03 = [];
    let dataChart04 = [];
    let dataChart05 = [];
    let dataChart06 = [];
    let dataChart07 = [];
    let dataChart08 = [];
    let dataChartMax = [];

   
    
    let lastDefinedIst = 0;
    let lastDefinedBudget = 0;
    let lastDefinedUV = 0;
    let lastDefinedErwartung = 0;
    let lastDefinedVerfügt = 0;
    let sumCumAll = 0;
 
    for (var i = 0; i < monthsLabels.length; i++) {
     
      let arr = []; 
      let sum = 0;
      let arr2 = []; 
      let sum2 = 0;
      
      
      
      
      arr = dataFilter.filter((item)=> item.DATE_RANGE === monthsLabels[i] && item.RESSOURCE === 'EL' && item.CO_STANDARD !== 6).map((item)=> item.KOSTEN)
      sum = arr.reduce((a, b) => a + b, 0);

      dataChart00.push(
        sum
      )

      sumCumAll += sum


      arr = dataFilter.filter((item)=> item.DATE_RANGE === monthsLabels[i] && item.RESSOURCE === 'FL'&& item.CO_STANDARD !== 6).map((item)=> item.KOSTEN)
      sum = arr.reduce((a, b) => a + b, 0);
      
      dataChart01.push(
        sum
      )

      sumCumAll += sum

      
      // if (!vorhabenSelect.length)
      // {
      //   arr = [...new Set(dataFilter.filter((item)=> item.DATE_RANGE === monthsLabels[i] ).map((item)=> item.CUM_ALL))]
      //   sum = arr.reduce((a, b) => a + b, 0);
      // }
      // else
      // {
        
      //   // Sum
      //   arr = [...new Set(dataFilter.filter((item)=> item.DATE_RANGE === monthsLabels[i] ).map((item)=> item.CUM_ALL))]
      //   sumCumAll = arr.reduce((a, b) => a + b, 0);
        
      //   arr = [...new Set(dataFilter_CUM.filter((item)=> item.DATE_RANGE === monthsLabels[i] && !vorhabenSelect.includes(item.VORHABEN_ID)).map((item)=> item.CUM))]
      //   sum = arr.reduce((a, b) => a + b, 0);

      //   sum = sumCumAll - sum
      // }
      
   
      
      dataChart02.push(
        sumCumAll
      )
     
      arr = [...new Set(dataFilter.filter((item)=> item.DATE_RANGE === monthsLabels[i] ).map((item)=> item.IST + item.ANZAHLUNG))]
      sum = arr.reduce((a, b) => a + b, 0);
      arr2 = [...new Set(dataFilter.filter((item)=> item.DATE_RANGE === monthsLabels[i-1] ).map((item)=> item.IST + item.ANZAHLUNG))]
      sum2 = arr2.reduce((a, b) => a + b, 0);
      
      
      if (sum >= lastDefinedIst) {
        lastDefinedIst = sum
      }
      else{
        sum = null; 
      }

      sum2 = (sum - sum2) > 0 ? (sum - sum2) : 0
      
      
      dataChart03.push(
        sum2
        
      )
      dataChart07.push(
        sum 
      )

   

      arr = [...new Set(dataFilter.filter((item)=> item.DATE_RANGE === monthsLabels[i] ).map((item)=> item.BUDGET))]
      sum = arr.reduce((a, b) => a + b, 0);
      
      if (sum === null || sum === 0) {
        sum = lastDefinedBudget; 
                  }
      else{
        lastDefinedBudget = sum;
      }
      
      dataChart04.push(
        sum
      )


       
      
     
      arr = [...new Set(dataFilter.filter((item)=> item.DATE_RANGE === monthsLabels[i] ).map((item)=> item.UV))]
      sum = arr.reduce((a, b) => a + b, 0);
      
      if (sum === null || sum === 0) {
        sum = lastDefinedUV; 
                  }
      else{
        lastDefinedUV = sum;
      }
    
    
     
      dataChart05.push(
        sum
      )
  
      arr = [...new Set(dataFilter.filter((item)=> item.DATE_RANGE === monthsLabels[i] ).map((item)=> item.ERWARTUNG - item.UV))]
      sum = arr.reduce((a, b) => a + b, 0);
      
      if (sum === null || sum === 0) {
        sum = lastDefinedErwartung; 
                  }
      else{
        lastDefinedErwartung = sum;
      }
      
     
      dataChart06.push(
        sum
      )


      arr = [...new Set(dataFilter.filter((item)=> item.DATE_RANGE === monthsLabels[i] ).map((item)=> item.IST + item.OBLIGO))]
      sum = arr.reduce((a, b) => a + b, 0);
      
      
      if (sum >= lastDefinedVerfügt) {
        lastDefinedVerfügt = sum
      }
      else{
        sum = null; 
      }
      
      dataChart08.push(
        sum
        
      )


       


     
     

    //   arr = dataFilter.filter((item)=> item.DATE_RANGE=== monthsLabels[i] && !paketArt.includes(item.TYP)).map((item)=> item.MINGESAMTKOSTEN*1000000)
    //   sum = arr.reduce((a, b) => a + b, 0);

    //   dataChart04.push(
    //     sum
    //   )

    //   arr = dataFilter.filter((item)=> item.DATE_RANGE=== monthsLabels[i] && !paketArt.includes(item.TYP)).map((item)=> item.MAXGESAMTKOSTEN*1000000)
    //   sum = arr.reduce((a, b) => a + b, 0);

    //   dataChartMax.push(
    //     sum
    //   )
     }
    //  console.log(monthsLabels)
    //  monthsLabels = monthsLabels.map(item => new Date(item))
    //  monthsLabels = monthsLabels.sort((a, b) => a - b );
    //  monthsLabels = monthsLabels.map(item => new Date(item).toLocaleString('DE-AT', { month: 'short',year: '2-digit'}))
    //  console.log(monthsLabels)
     

     let arr = []; 

    arr = dataFilter.filter((item)=> item.RESSOURCE === 'EL' && item.CO_STANDARD !== 6).map((item)=> item.KOSTEN)
    let sumEL = arr.reduce((a, b) => a + b, 0);
    arr = dataFilter.filter((item)=>  item.RESSOURCE === 'FL' && item.CO_STANDARD !== 6).map((item)=> item.KOSTEN)
    let sumFL = arr.reduce((a, b) => a + b, 0);


    arr = dataFilter.filter((item)=> item.CO_STANDARD === 0).map((item)=> item.KOSTEN)
    let sumPSP00 = arr.reduce((a, b) => a + b, 0);
    arr = dataFilter.filter((item)=>  item.CO_STANDARD === 1).map((item)=> item.KOSTEN)
    let sumPSP01 = arr.reduce((a, b) => a + b, 0);
    arr = dataFilter.filter((item)=> item.CO_STANDARD === 2).map((item)=> item.KOSTEN)
    let sumPSP02 = arr.reduce((a, b) => a + b, 0);
    arr = dataFilter.filter((item)=>  item.CO_STANDARD === 3).map((item)=> item.KOSTEN)
    let sumPSP03 = arr.reduce((a, b) => a + b, 0);
    arr = dataFilter.filter((item)=> item.CO_STANDARD === 4).map((item)=> item.KOSTEN)
    let sumPSP04 = arr.reduce((a, b) => a + b, 0);
    arr = dataFilter.filter((item)=>  item.CO_STANDARD === 5).map((item)=> item.KOSTEN)
    let sumPSP05 = arr.reduce((a, b) => a + b, 0);
    arr = dataFilter.filter((item)=> item.CO_STANDARD === 6).map((item)=> item.KOSTEN)
    let sumPSP06 = arr.reduce((a, b) => a + b, 0);
    arr = dataFilter.filter((item)=>  item.CO_STANDARD === 7).map((item)=> item.KOSTEN)
    let sumPSP07 = arr.reduce((a, b) => a + b, 0);

    
  //  let  lastNonNull = dataChart07.filter(x => x != null).slice(-1)[0]
   setIst(lastDefinedIst)
   setBudget(lastDefinedBudget)
   setErwartung(lastDefinedErwartung)
   setVerfügt(lastDefinedVerfügt)
     
  
    // arr = dataFilter.filter((item)=> item.TYP === 'GroßPakete').map((item)=> item.MINGESAMTKOSTEN*1000000)
    // let sumPSP06 = arr.reduce((a, b) => a + b, 0);
    // arr = dataFilter.filter((item)=> item.TYP === 'GroßPakete').map((item)=> item.MAXGESAMTKOSTEN*1000000)
    // let sumPSP07 = arr.reduce((a, b) => a + b, 0);

    // arr = dataFilter.filter((item)=> item.TYP === 'OhnePaket').map((item)=> item.MINGESAMTKOSTEN*1000000)
    // let sumOPMin = arr.reduce((a, b) => a + b, 0);
    // arr = dataFilter.filter((item)=> item.TYP === 'OhnePaket').map((item)=> item.MAXGESAMTKOSTEN*1000000)
    // let sumOPMax = arr.reduce((a, b) => a + b, 0);

    // arr = dataFilter.filter((item)=> item.TYP === 'KleinPakete').map((item)=> item.MINGESAMTKOSTEN*1000000)
    // let sumKPMin = arr.reduce((a, b) => a + b, 0);
    // arr = dataFilter.filter((item)=> item.TYP === 'KleinPakete').map((item)=> item.MAXGESAMTKOSTEN*1000000)
    // let sumKPMax = arr.reduce((a, b) => a + b, 0);

    // let sumSP = dataChart00.reduce((a, b) => a + b, 0)
    // let sumGP = dataChart01.reduce((a, b) => a + b, 0)
    // let sumOP = dataChart02.reduce((a, b) => a + b, 0)
    // let sumKP = dataChart03.reduce((a, b) => a + b, 0)
    // let sumGesamt = sumSP + sumGP + sumOP + sumKP

    // let przSP = (sumSP*100/sumGesamt).toFixed(1)
    // let przGP = (sumGP*100/sumGesamt).toFixed(1)
    // let przOP = (sumOP*100/sumGesamt).toFixed(1)
    // let przKP = (sumKP*100/sumGesamt).toFixed(1)

    // sumSP = sumSP.toLocaleString("de-DE",{style:"currency", currency:"EUR", maximumFractionDigits: 0});
    // sumEL = sumEL.toLocaleString("de-DE",{style:"currency", currency:"EUR", maximumFractionDigits: 0});
    // sumFL = sumFL.toLocaleString("de-DE",{style:"currency", currency:"EUR", maximumFractionDigits: 0});

    // sumGP = sumGP.toLocaleString("de-DE",{style:"currency", currency:"EUR", maximumFractionDigits: 0});
    // sumPSP06 = sumPSP06.toLocaleString("de-DE",{style:"currency", currency:"EUR", maximumFractionDigits: 0});
    // sumPSP07 = sumPSP07.toLocaleString("de-DE",{style:"currency", currency:"EUR", maximumFractionDigits: 0});

    // sumOP = sumOP.toLocaleString("de-DE",{style:"currency", currency:"EUR", maximumFractionDigits: 0});
    // sumOPMin = sumOPMin.toLocaleString("de-DE",{style:"currency", currency:"EUR", maximumFractionDigits: 0});
    // sumOPMax = sumOPMax.toLocaleString("de-DE",{style:"currency", currency:"EUR", maximumFractionDigits: 0});

    // sumKP = sumKP.toLocaleString("de-DE",{style:"currency", currency:"EUR", maximumFractionDigits: 0});
    // sumKPMin = sumKPMin.toLocaleString("de-DE",{style:"currency", currency:"EUR", maximumFractionDigits: 0});
    // sumKPMax = sumKPMax.toLocaleString("de-DE",{style:"currency", currency:"EUR", maximumFractionDigits: 0});
    

    //console.log(sumEL)
    
    // setSumSP(sumSP);
    // setPrzSP(przSP);
    setSumEL(sumEL);
    setSumFL(sumFL);

    // setSumGP(sumGP);
    // setPrzGP(przGP)
    setsumPSP00(sumPSP00);
    setsumPSP01(sumPSP01);
    setsumPSP02(sumPSP02);
    setsumPSP03(sumPSP03);
    setsumPSP04(sumPSP04);
    setsumPSP05(sumPSP05);
    setsumPSP06(sumPSP06);
    setsumPSP07(sumPSP07);
    setErwartung(sumEL+sumFL+sumPSP06)

    // setSumOP(sumOP);
    // setPrzOP(przOP)
    // setSumOPMin(sumOPMin);
    // setSumOPMax(sumOPMax);

    // setSumKP(sumKP);
    // setPrzKP(przKP)
    // setSumKPMin(sumKPMin);
    // setSumKPMax(sumKPMax);
    



    setchart00(dataChart00);
    setChart01(dataChart01);
    setChart02(dataChart02);
    setChart03(dataChart03);
    setChart04(dataChart04);
    setChart05(dataChart05);
    setChart06(dataChart06);
    setChart07(dataChart07);
    setChartMax(dataChart02);
    setLabels(monthsLabels);
   
    
    // setmitarbeiterItems(gantt_werk); 
    
  } 
  
  }, [data,paketSelect,vorhabenSelect,mitarbeiterSelect,timeStart,timeEnd, paketArt])   
  

  useEffect(() => {
    if (maData){


      let dataFilter = []
      dataFilter = maData
      let uniqMitarbeiter = dataFilter.filter(({PERSONALNR}, index, a) => a.findIndex(e => PERSONALNR === e.PERSONALNR) === index);
    
      setCurrentMitarbeiterItems(
        uniqMitarbeiter.map(item =>
          item.PERSONALNR !== 0
          ?
          {
                id: item.KURZZEICHEN,
                title: item.KURZZEICHEN,
                team: item.TEAM,   
          }
          : item
          ))
        }
         
       
     
      
  }, [maData])

  
  
  

  if (error) return <h1>... Please wait</h1>
  if (!data) return ( 
                <Box sx={{ width: '100%' , paddingBottom:1,paddingTop:1}}>
                 <LinearProgress/>
                 <h1> ... Loading Data</h1>
               </Box>
                  );


  
  const handleClick = (event) => {
    setAnchorEl(event.currentTarget);
  
  };

  const handlePreSelection = (event) => {
    let _name = event.target.getAttribute("name")
    let _range = Number(event.target.getAttribute("value"))
    // _range -= 1
      
  
    if (_name==='gesamter Zeitraum')
    {
      setFrom(moment().startOf('year').add(-10,'year').unix());
      setTo(moment().endOf('year').add(20,'year').unix());
    }
    else 
    {
      setFrom(moment().startOf('year').add(_range,'year').unix());
      setTo(moment().endOf('year').add(_range,'year').unix());
    }

  }

  const handelDateRangePickerFrom = (newValue) => {
    setFrom(moment(newValue).unix())

    if (newValue >= to) {
      setTo(moment(newValue).unix())
    }    
  }

  const handelDateRangePickerTo = (newValue) => {
    setTo(moment(newValue).unix())

      if (newValue <= from) {
        setFrom(moment(newValue).unix())
      }     
   }

  const handleClose = () => {
    

  
    setTimeStart(from)
    setTimeEnd(to)
    setAnchorEl(null);
    
  
  };

  const handleMenuClose = () =>{
    setAnchorEl(null);
  }
  
  const handleprevious = () => {
    
    const zoom = timeEnd - timeStart;
    setFrom(timeStart - zoom)
    setTo(timeEnd - zoom)
    setTimeStart(timeStart - zoom);
    setTimeEnd(timeEnd - zoom);
   
  
  };
  
  const handlenext = () => {
  
    const zoom = timeEnd - timeStart;
    setFrom(timeStart + zoom)
    setTo(timeEnd + zoom)
    setTimeStart(timeStart +  zoom);
    setTimeEnd(timeEnd + zoom );
  
  };
  

  
  const handlePaektFilter = (event) => {

    const value = event.target.value;
    let filteredItems = [...new Set(paketItems.filter(item => item.title.toLowerCase().indexOf(searchTextPaket.toLowerCase()) > -1).map(item => item.id))]
    if (value[value.length - 1] === "All") {
      setPaketSelect(paketSelect.length === filteredItems.length ? [] : filteredItems);
      setVorhabenSelect([])
      setSearchTextVorhaben('')
      return;
    }
    setPaketSelect(value);
    setVorhabenSelect([])
    setSearchTextVorhaben('')
    // setMitarbeiterSelect([])
  
  
   };
  
  const handleVorhabenFilter = (event) => {
    const value = event.target.value;
    let filteredItems = [...new Set(vorhabenItems.filter(item => item.title.toLowerCase().indexOf(searchTextVorhaben.toLowerCase()) > -1).map(item => item.id))]
    if (value[value.length - 1] === "All") {
      setVorhabenSelect(vorhabenSelect.length === filteredItems.length ? [] : filteredItems);
      // setMitarbeiterSelect([])
      return;
    }
    setVorhabenSelect(value);
    // setMitarbeiterSelect([])
    
  };
  
  // const handleMitarbeiterFilter = (event) => {
  //   const {
  //     target: { value },
  //   } = event;
  
  //   if (value[value.length - 1] === "All") {
  //     setMitarbeiterSelect(mitarbeiterSelect.length === mitarbeiterItems.length ? [] : [...new Set(mitarbeiterItems.map(item => item.id))]);
  //     return;
  //   }
    
  //     setMitarbeiterSelect(value)
  //     setPaketSelect([]);
  //     setVorhabenSelect([]);
  
      
   
  // };


  const handleCurrentMitarbeiterFilter = (event) => {
    const {
      target: { value },
    } = event;
  
    if (value.includes("All")) {
      setCurrentMitarbeiterSelect([]) 
      // currentMitarbeiterSelect.length === currentMitarbeiterItems.length ? [] : [...new Set(currentMitarbeiterItems.map(item => item.id))]);
      setCurrentUser(user.ABBREVATION)
      setCurrentTeam(user.TEAM)
      return;
    }
    else{
      
      setCurrentMitarbeiterSelect( typeof value === 'string'  ? value.split(',') : value,)
      setCurrentUser(value)
      setCurrentTeam(maData.filter(item => item.KURZZEICHEN === value).map(item => item.TEAM))
     

    }

    setPaketSelect([]);
    setVorhabenSelect([]);
    // setMitarbeiterSelect([]);
    setQueryVID([])
    setSqlOption('0')
   
    

    
   
  };

  const handleGroupChange = (event) => {
      setGroupView(event.target.value)

    if (event.target.value !== '4'){ 
      setSqlOption(event.target.value)
      
     }
    setPaketSelect([]);
    setVorhabenSelect([])
    setSearchTextPaket('')
    setSearchTextVorhaben('')
    // setMitarbeiterSelect([])
   
  };

 


// const LegendClickHandler = function(e, legendItem, legend) {


//   var hiddenItems = [];
//   hiddenItems = legend.legendItems.filter(item => item.hidden === true).map(item => item.text)
//   // console.log(hiddenItems)
//   setPaketArt(hiddenItems)
  
// }

const headCells = [
  {
    id: 'name',
    numeric: false,
    disablePadding: true,
    label: 'Dessert (100g serving)',
  },
  {
    id: 'calories',
    numeric: true,
    disablePadding: false,
    label: 'Calories',
  },
  {
    id: 'fat',
    numeric: true,
    disablePadding: false,
    label: 'Fat (g)',
  },
  {
    id: 'carbs',
    numeric: true,
    disablePadding: false,
    label: 'Carbs (g)',
  },
  {
    id: 'protein',
    numeric: true,
    disablePadding: false,
    label: 'Protein (g)',
  },
];



   
  

  
  return (
    
    <div>
      <Grid   container
        direction="row"
        justifyContent="flex start"
        alignItems="center"
        sx={{ paddingBottom:1,paddingTop:1}}>
                    <Controls.SearchSelect
                        name = "Peket"
                        label = "Paket"
                        value = {paketSelect}
                        onChange={handlePaektFilter}
                        options={paketItems}
                        multiple={true}
                        searchText={searchTextPaket}
                        setSearchText={setSearchTextPaket}
                       
                    />

                    <Controls.SearchSelect
                        name = "Vorhaben"
                        label = "Vorhaben"
                        value = {vorhabenSelect}
                        onChange={handleVorhabenFilter}
                        options={vorhabenItems}
                        multiple={true}
                      searchText={searchTextVorhaben}
                       setSearchText={setSearchTextVorhaben}
                      
                       
                    />
                    {/* <Controls.SearchSelect
                        name = "Mitarbeiter"
                        label = "Mitarbeiter"
                        value = {mitarbeiterSelect}
                        onChange={handleMitarbeiterFilter}
                        options={mitarbeiterItems}
                        multiple={true}
                        searchText={searchText}
                        setSearchText={setSearchText}
                       
                    /> */}


                    <Controls.ControlledSwitch
                    label='Quartal / Monat'
                    onChange={e => setChecked(e.target.checked)}
                    checked={checked}

                    />

          <Box sx={{ display: 'flex', alignItems: 'center', pt: 1 ,}}>
          <IconButton aria-label="previous"  onClick={handleprevious}>
             <SkipPreviousIcon />
          </IconButton>
 
          <IconButton id="basic-button"
          aria-controls="basic-menu"
          aria-haspopup="true"
          aria-expanded={open ? 'true' : undefined}
          onClick={handleClick}

          >
             <DateRangeOutlinedIcon  />
             </IconButton>
              <Menu
                id="basic-menu"
                anchorEl={anchorEl}
                open={open}
                onClose={handleMenuClose}
                MenuListProps={{
                  'aria-labelledby': 'basic-button',
                }}
              > 
              <Controls.BasicDateRangePicker
                from={from}
                to={to}
                onChangeFrom={handelDateRangePickerFrom}
                onChangeTo={handelDateRangePickerTo}
              
              />
               <MenuItem   value="-1"  name="letztes Jahr" onClick={handlePreSelection} >letztes Jahr</MenuItem>
                <MenuItem value="0"  name="aktuelles Jahr" onClick={handlePreSelection}>aktuelles Jahr</MenuItem>
                <MenuItem value="1"  name="nächstes Jahr" onClick={handlePreSelection}>nächstes Jahr</MenuItem>
                <MenuItem value="20"  name="gesamter Zeitraum" onClick={handlePreSelection}>gesamter Zeitraum</MenuItem>
                {/* <MenuItem value="30"  name="year" onClick={handleClose}>30 years</MenuItem>
                <MenuItem value="50"  name="year" onClick={handleClose}>50 years</MenuItem> */}
                 <Divider />
                 <MenuItem>
                 <Controls.Button 
                  onClick={handleClose}
                  text={'Übernehmen'}
                  />
                 </MenuItem>
              </Menu>  

              <IconButton aria-label="next"  onClick={handlenext}>
             <SkipNextIcon />
          </IconButton>
        </Box>

        <Controls.RadioGroup
                    name='ansicht'
                    label='Ansicht'
                    value={groupView}
                    onChange={handleGroupChange}
                    items={genderItems}
                    
                    />
        <Controls.SearchSelect
                        name = "Mitarbeiter"
                        label = "Mitarbeiter"
                        value = {currentMitarbeiterSelect}
                        onChange={handleCurrentMitarbeiterFilter}
                        options={currentMitarbeiterItems}
                        multiple={false}
                        disabled={groupView === '4' ? false : true}
                        searchText={searchTextCurrentMitarbeiter}
                        setSearchText={setSearchTextCurrentMitarbeiter}
                    />
          
      </Grid>
      <Divider />
      <Grid  container
         direction="row"
         justifyContent="space-around"
         alignItems="center"
         sx={{pt:2}}
        //style={{ gaping: 20}}
        >

      {/* *******************************************************************************************************  */}
      <Box sx={{bgcolor: 'background.paper',boxShadow: 1,borderRadius: 1, p: 2, width: 350 }}>
        <Grid container justifyContent="space-between" alignItems="center">
          <Grid>
            <Box sx={{ color: 'text.primary' , display: 'inline', fontWeight: 'medium'}}>Budget</Box>
          </Grid>
          <Grid>
            <Box sx={{ color: 'text.primary', fontSize: 18, fontWeight: 'medium' }}>
              {(budget).toLocaleString("de-DE",{style:"currency", currency:"EUR", maximumFractionDigits: 0})}
            </Box>
          </Grid>
        </Grid>
          <Box sx={{ color: 'text.secondary', fontSize: 12, fontWeight: 'medium'  }}>
            <Stack direction="row" justifyContent="space-between" alignItems="flex-end"spacing={2}>
                <Gauge data={[ist,verfügt - ist, (budget -verfügt)<0 ? 0 : budget -verfügt]} maxValue={budget}  labels={['Ist','Verfügt','Verfügbar']} color={[color06,color04,'lightgrey']} rotation={0} />
                <Stack direction="column" justifyContent="felx-end" alignItems="flex-end" spacing={1}>
                  <Grid container direction="row" alignItems="center" justifyContent="space-between" spacing={1}>
                    <CreditScoreIcon sx={{ color: color06}}/> 
                    {`${ist.toLocaleString("de-DE",{style:"currency", currency:"EUR", maximumFractionDigits: 0})}`}
                  </Grid>
                  <Grid container direction="row" alignItems="center" justifyContent="space-between" spacing={1}>
                    <CreditCardIcon sx={{ color: color04}} />
                    {`${(verfügt).toLocaleString("de-DE",{style:"currency", currency:"EUR", maximumFractionDigits: 0})}`}
                  </Grid> 

              </Stack>
            </Stack>
          </Box>
      </Box>
     
    

      {/* *******************************************************************************************************  */}
      <Box sx={{bgcolor: 'background.paper',boxShadow: 1,borderRadius: 1, p: 2, width: 350 }}>
        <Grid container justifyContent="space-between" alignItems="center">
          <Grid>
            <Box sx={{ color: 'text.primary' , display: 'inline', fontWeight: 'medium'}}>UV {' & '} Gleitung</Box>
          </Grid>
          <Grid>
            <Box sx={{ color: 'text.primary', fontSize: 18, fontWeight: 'medium' }}>
              {(sumPSP06 + sumPSP07).toLocaleString("de-DE",{style:"currency", currency:"EUR", maximumFractionDigits: 0})}
            </Box>
          </Grid>
        </Grid>
          <Box sx={{ color: 'text.secondary', fontSize: 12, fontWeight: 'medium'  }}>
            <Stack direction="row" justifyContent="space-between" alignItems="flex-end"spacing={2}>
                <Doughnut data={[sumPSP06,sumPSP07,erwartung]}    labels={['UV','Gleitung','Gesamt']} color={[color05,color07,'lightgrey']} rotation={0} />
                <Stack direction="column" justifyContent="felx-end" alignItems="flex-end" spacing={1}>
                  <Grid container direction="row" alignItems="center" justifyContent="space-between" spacing={1}>
                    <AddShoppingCartSharpIcon sx={{ color: color05}}/>
                    {`${sumPSP06.toLocaleString("de-DE",{style:"currency", currency:"EUR", maximumFractionDigits: 0})}`}
                  </Grid>
                  <Grid container direction="row" alignItems="center" justifyContent="space-between" spacing={1}>
                    <ShoppingCartCheckoutIcon sx={{ color: color07}} />
                    {`${sumPSP07.toLocaleString("de-DE",{style:"currency", currency:"EUR", maximumFractionDigits: 0})}`}
                  </Grid> 
              </Stack>
            </Stack>
          </Box>
      </Box>
     
      {/* *******************************************************************************************************  */}
      <Box sx={{bgcolor: 'background.paper',boxShadow: 1,borderRadius: 1, p: 2, width: 350 }}>
        <Grid container justifyContent="space-between" alignItems="center">
          <Grid>
            <Box sx={{ color: 'text.primary' , display: 'inline', fontWeight: 'medium'}}>PSP Elemente</Box>
          </Grid>
          <Grid>
            <Box sx={{ color: 'text.primary', fontSize: 18, fontWeight: 'medium' }}>
              {(sumPSP00 + sumPSP01 + sumPSP02+ sumPSP03+ sumPSP04).toLocaleString("de-DE",{style:"currency", currency:"EUR", maximumFractionDigits: 0})}
            </Box>
          </Grid>
        </Grid>
          <Box sx={{ color: 'text.secondary', fontSize: 12, fontWeight: 'medium'  }}>
            <Stack direction="row" justifyContent="space-between" alignItems="flex-end"spacing={2}>
                <BarChart  
                
                    data={[sumPSP00,sumPSP01,sumPSP02,sumPSP03,sumPSP04,sumPSP05]}
                    labels={['0','1','2','3','4','5']} 
                    color={[color00,color01,color02,color03,color04,color05]}
                    // data0={[sumPSP00,erwartung]} 
                    // data1={[sumPSP01,erwartung]} 
                    // data2={[sumPSP02,erwartung]} 
                    // data3={[sumPSP03,erwartung]} 
                    // data4={[sumPSP04,erwartung]} 
                    // data5={[sumPSP05,erwartung]} 
                    // data6={[sumPSP06,erwartung]} 
                    // data7={[sumPSP07,erwartung]} 

                    // labels={['PSP','PSP']} 

                    // color0={[color00,'lightgrey']}
                    // color1={[color01,'lightgrey']}
                    // color2={[color02,'lightgrey']}
                    // color3={[color03,'lightgrey']}
                    // color4={[color04,'lightgrey']}
                    // color5={[color05,'lightgrey']}
                    // color6={[color06,'lightgrey']}
                    // color7={[color07,'lightgrey']}
                    />
                {/* <Stack direction="column" justifyContent="felx-end" alignItems="flex-end" spacing={1}>
                  <Grid container direction="row" alignItems="center" justifyContent="space-between" spacing={2}>
                    <AddShoppingCartSharpIcon sx={{ color: color05}}/>
                    {`${sumPSP06.toLocaleString("de-DE",{style:"currency", currency:"EUR", maximumFractionDigits: 0})}`}
                  </Grid>
                  <Grid container direction="row" alignItems="center" justifyContent="space-between" spacing={1}>
                    <ShoppingCartCheckoutIcon sx={{ color: color07}} />
                    {`${sumPSP07.toLocaleString("de-DE",{style:"currency", currency:"EUR", maximumFractionDigits: 0})}`}
                  </Grid> 
              </Stack> */}
            </Stack>
          </Box>
      </Box>

      {/* *******************************************************************************************************  */}
      <Box sx={{bgcolor: 'background.paper',boxShadow: 1,borderRadius: 1, p: 2, width: 350 }}>
          <Grid container justifyContent="space-between" alignItems="center">
            <Grid>
              <Box sx={{ color: 'text.primary' , display: 'inline', fontWeight: 'medium'}}>EL {' & '} FL</Box>
            </Grid>
            <Grid>
              <Box sx={{ color: 'text.primary', fontSize: 18, fontWeight: 'medium' }}>
                {(sumEL + sumFL).toLocaleString("de-DE",{style:"currency", currency:"EUR", maximumFractionDigits: 0})}
              </Box>
            </Grid>
          </Grid>
            <Box sx={{ color: 'text.secondary', fontSize: 12, fontWeight: 'medium'  }}>
              <Stack direction="row" justifyContent="space-between" alignItems="flex-end"spacing={2}>
                  <PiChart data={[sumEL,sumFL]} labels={['EL','FL']} color={[color00,color01]} rotation={0} />
                  <Stack direction="column" justifyContent="felx-end" alignItems="flex-end" spacing={2}>
                    <Grid container direction="row" alignItems="center" justifyContent="space-between" spacing={1}>
                      <EngineeringSharpIcon sx={{ color: color00}}/>
                      {`${sumEL.toLocaleString("de-DE",{style:"currency", currency:"EUR", maximumFractionDigits: 0})}`}
                    </Grid>
                    <Grid container direction="row" alignItems="center" justifyContent="space-between" spacing={1}>
                      <ShoppingCartOutlinedIcon sx={{ color: color01}} />
                      {`${sumFL.toLocaleString("de-DE",{style:"currency", currency:"EUR", maximumFractionDigits: 0})}`}
                    </Grid> 
                </Stack>
              </Stack>
            </Box>
        </Box>

   

    </Grid>
  
      
     
      <p></p>
     
       

      <Grid  container
        // direction="row"
        columns={{ xs: 5.6, sm: 5.6, md: 12 }}
        justifyContent="center"
        spacing={2}
        //alignItems="center"
        //</div>style={{ gap: 15 }}
        >
        
        {/* ********************************************************************************************************************* */}
        <Grid Grid item xs={5.6} sm={5.6} md={5.6}>
        <Card >
          <CardHeader style={{ textAlign: 'center', height: '60px' , background: 'linear-gradient(45deg, #138D75 30%, #2FD5B4 90%)'}}
            avatar={
              <Avatar  variant="rounded" style={{color:'#138D75', background:'#2FD5B4'}}>
              <EuroIcon />
              </Avatar>
            }
            titleTypographyProps={{
            fontSize: 22,
            color: 'white'
            }}
            subheaderTypographyProps={{
            fontSize: 18,
            color: 'white'
            }}
            title={`Budget/ Erwartung / Kosten`} 
            subheader={`Verlauf`} 
          />
          <CardContent>
            <MixedChart  
            // label00 ='Eigenleistung' 
            // data00={chart00} 
            // label01 ='Fremdleistung' 
            // data01={chart01}
            label02 ='Erwartung' 
            data02={chart02}
            // label03 ='Ist' 
            // data03={chart03}
            label04 ='Budget' 
            data04={chart04}
            label05 ='UV' 
            data05={chart05}
            label06 ='Erwartung' 
            data06={chart06}
            label07 ='Ist' 
            data07={chart07}
            // labelMax ='max Kosten' 
            // dataMax={chartMax}
            labels={labels} 
            // LegendClickHandler={LegendClickHandler}
            // paketArt={paketArt}
            timerange={checked ? 'month' : 'quarter'}
            />
          </CardContent>
        </Card>
      </Grid>

      {/* ********************************************************************************************************************* */}
      <Grid Grid item xs={5.6} sm={5.6} md={5.6}>
        <Card >
          <CardHeader style={{ textAlign: 'center', height: '60px' , background: 'linear-gradient(45deg, #2FD5B4 30%, #138D75 90%)'}}
            avatar={
              <Avatar  variant="rounded" style={{color:'#2FD5B4', background:' #138D75'}}>
              <EuroIcon />
              </Avatar>
            }
            titleTypographyProps={{
            fontSize: 22,
            color: 'white'
            }}
            subheaderTypographyProps={{
            fontSize: 18,
            color: 'white'
            }}
            title={`Erwartung / Kosten`} 
            subheader={`Eigen u. Fremdleistung`} 
          />
          <CardContent>
            <MixedChart  
            label00 ='Eigenleistung' 
            data00={chart00} 
            label01 ='Fremdleistung' 
            data01={chart01}
            // label02 ='Erwartung' 
            // data02={chart02}
            label03 ='Ist' 
            data03={chart03}
            // label04 ='Budget' 
            // data04={chart04}
            // label05 ='UV' 
            // data05={chart05}
            // label06 ='Erwartung' 
            // data06={chart06}
            // labelMax ='max Kosten' 
            // dataMax={chartMax}
            labels={labels} 
            // LegendClickHandler={LegendClickHandler}
            // paketArt={paketArt}
            timerange={checked ? 'month' : 'quarter'}
            />
          </CardContent>
        </Card>
        </Grid>

      
      {user.ABBREVATION==='JR' && (
        <Grid  item xs={11.2} sm={11.2} md={11.2}>
              <MUITable
              headCells={headCells}
              >
              
              </MUITable>
        </Grid>
      )}

     
      
      </Grid>
     
      
      
    
    </div>
  );
      }
