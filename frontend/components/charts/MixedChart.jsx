import React, { useRef, useEffect, useState } from "react";
import { Chart } from 'chart.js';
import 'chartjs-adapter-moment';
import ChartDataLabels from 'chartjs-plugin-datalabels';





const color00 = 'rgba(0, 153, 153,1)';
const color01 = 'rgba(0, 204, 204, 1)';
const color02 = 'rgba(0, 255, 255, 1)';
const color03 = 'rgba(153, 255, 255, 1)';
const color04 = 'rgba(102, 204, 255, 1)';
const color05= 'rgba(102, 153, 204, 1)';
const color06 = 'rgba(0, 102, 153 , 1)';
const color07 = 'rgba(204, 102, 153,1)';


const MixedChart = ({ 
  label00,
  label01,
  label02,
  label03,
  label04,
  label05,
  label06,
  label07,  
  data00,
  data01,
  data02,
  data03,
  data04,
  data05,
  data06,
  data07,
  dataMax,
  labels,
  timerange,
  LegendClickHandler,
  paketArt}) => {
  
  const chartRef = useRef(null);
  const [myChart, setMyChart] = useState(null);
  


  useEffect(() => {
    if (!chartRef) return;
    // Chart.register(ChartDataLabels);
    const ctx = chartRef.current.getContext("2d");
    const gradient02 = ctx.createLinearGradient(0, 0, 0, 400);
    const gradient03 = ctx.createLinearGradient(0, 0, 0, 400);
    gradient02.addColorStop(0.75, 'rgba(47, 213, 180 ,0.15)');
    gradient02.addColorStop(0.5, 'rgba(47, 213, 180 ,0.3)');
    gradient02.addColorStop(0.25, 'rgba(47, 213, 180 ,0.45)');
    
    gradient03.addColorStop(0.75, 'rgba(153, 255, 255 ,0.25)');
    gradient03.addColorStop(0.5, 'rgba(153, 255, 255 ,0.5)');
    gradient03.addColorStop(0.25, 'rgba(153, 255, 255 ,0.75)');

    const cursor = {
      id: 'cursor',
      afterDraw (chart) {
        if (chart.tooltip?._active?.length) {
            let x = chart.tooltip._active[0].element.x;
            let y = chart.scales.y;
            let ctx = chart.ctx;
            ctx.save();
            ctx.beginPath();
            ctx.moveTo(x, y.top);
            ctx.lineTo(x, y.bottom);
            ctx.lineWidth = 1;
            ctx.strokeStyle = '#ff0000';
            ctx.stroke();
            ctx.restore();
        }
    },


    }
   

     
    // const maxYaxis = Math.max(...dataMax)
    // console.log(Math.max(...dataMax))
    // console.log(maxYaxis)

    const footer = (tooltipItems) => {
      let sum = 0;
    
      tooltipItems.forEach(function(tooltipItem) {
        if (tooltipItem.datasetIndex < 2){
        sum += tooltipItem.parsed.y;
        }
      });
      sum = sum.toLocaleString("de-DE",{style:"currency", currency:"EUR", maximumFractionDigits: 0});
      return 'Gesamt: ' + sum;
    };

    const filter =  (tooltipItem) => {
      return tooltipItem.datasetIndex < 10;
    };

    const legendFilter = (legendItem, data) => {
      let label = data.datasets[legendItem.datasetIndex].label || '';
      if (typeof(label) !== 'undefined') {
         if (legendItem.datasetIndex >= 10){
          return false;
        }
      }
      return label;
    }




    const myChart = new Chart(ctx, {
      data: {
        labels: labels,
        datasets: [
          {
            label: label00,
            data: [],
            fill: true,
            type: "bar", 
            backgroundColor: color00,
            borderColor: 'gray',
            borderWidth: 2,
            stack: "y",
           // yAxisID: 'y',
            order: 3
          },
          {
            label: label01,
            data: [],
            fill: true,
            type: "bar", 
            backgroundColor: color01,
            borderColor: 'gray',
            borderWidth: 2,
            stack: "y",
           // yAxisID: 'y',
            order: 2
          },
          {
            label: label02,
            data: [],
            fill: true,
            type: "line", 
            backgroundColor: gradient02,
            borderColor: 'grey',
            cubicInterpolationMode: 'monotone',
            borderWidth: 2,
            // stack: "y-axis-1",
           // yAxisID: 'y',
            order: 4
          },
          {
            label: label03,
            data: [],
            fill: true,
            type: "line", 
            backgroundColor: gradient03,
            borderColor: 'black',
            cubicInterpolationMode: 'monotone',
            borderWidth: 2,
            // stack: "y-axis-1",
           // yAxisID: 'y',
            order: 1
          },
          {
            label: label04,
            data: [],
            fill: false,
            type: "line", 
            backgroundColor: 'rgba(0,0,0, 0)',
            borderColor:  color04,
            cubicInterpolationMode: 'monotone',
            borderWidth: 3,
            // stack: "y-axis-2",
           // yAxisID: 'y',
            order: 5
          },
          {
            label: label05,
            data: [],
            fill: false,
            type: "line", 
            backgroundColor: 'rgba(0,0,0, 0)',
            borderColor:  color05,
            cubicInterpolationMode: 'monotone',
            borderWidth: 3,
            // stack: "y-axis-2",
           // yAxisID: 'y',
            order: 6
          },
          {
            label: label06,
            data: [],
            fill: false,
            type: "line", 
            backgroundColor:  'rgba(0,0,0, 0)',
            borderColor:  color06,
            cubicInterpolationMode: 'monotone',
            borderWidth: 3,
            // stack: "y-axis-2",
           // yAxisID: 'y',
            order: 7
          },
          {
          label: label07,
          data: [],
          fill: true,
          type: "line", 
          backgroundColor: gradient03,
          borderColor: 'black',
          cubicInterpolationMode: 'monotone',
          borderWidth: 2,
          // stack: "y-axis-1",
         // yAxisID: 'y',
          order: 3
        },
          
        ]
      },
      plugins: [ChartDataLabels,cursor],
      options:  {
        //events: ["click"],  
        elements: {
            point:{
                radius: 0
            }
        },
   
        
        responsive: true,
        maintainAspectRatio: false,
        intersect: true,

          interaction: {
            intersect: false,
            mode: 'index',
          },

        plugins: {
          
          legend:   {
            labels: {
              filter: legendFilter
            },
          //             onClick: function (e, legendItem, legend) {
          //               Chart.defaults.plugins.legend.onClick(e, legendItem, legend);
          //               LegendClickHandler(e, legendItem, legend);
          //           },
                    },
          datalabels: {
            display: false,
          },
          tooltip: {
          //         filter: filter,
                  callbacks: {
                              label: function(context) {
                                  let label = context.dataset.label || '';

                                  if (label) {
                                      label += ': ';
                                  }
                                  if (context.parsed.y !== null) {
                                      label += new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR',maximumFractionDigits: 0 }).format(context.parsed.y);
                                  }
                                  return label;
                              },
          //                     footer: footer,  
                  },
                
                  },
              },
        
        scales: {
            x: {
                stacked: true,
                display: true,
                ticks: { 
                    display: true 
                    
                },
                type: 'time',
                time: {
                    unit: timerange
                },
                grid: {
                    display: false,
                    drawBorder: false
                },
            
            },
            y: {
                 id: "y-axis-1",
                // stacked: true,
                display: true,
                // min: 0,
                // suggestedMax: maxYaxis,
                ticks: { 
                    display: true,
                    //stepSize: 25 
                      callback: (value, index, values) => {
                        return new Intl.NumberFormat("de-DE",{style:"currency", currency:"EUR", maximumFractionDigits: 0}).format(value);
                      }
                      },
                // grid: {
                //         drawOnChartArea: false, // only want the grid lines for one axis to show up
                //       },
                }
                // },
            // y1:{
            //     // id: "y-axis-2",
            //     stacked: false,
            //     display: false,
            //     position: 'left',
            //     min: 0,
            //     // suggestedMax: maxYaxis,
            //     ticks: { 
            //         display: true,
                   
            //         // stepSize: 25 
            //         callback: (value, index, values) => {
            //           return new Intl.NumberFormat("de-DE",{style:"currency", currency:"EUR", maximumFractionDigits: 0}).format(value);
            //         }
            //         },
            //      gridLines: {
            //           display: true,
            //           drawBorder: false
    
            // }
        }
      },
    });
    setMyChart(myChart);
  
  }, [chartRef]);

  useEffect(() => {
    if (!myChart) return;
    // const maxYaxis = Math.max(...dataMax)
    
    myChart.data.datasets[0].data = data00;
    myChart.data.datasets[1].data = data01;
    myChart.data.datasets[2].data = data02;
    myChart.data.datasets[3].data = data03;
    myChart.data.datasets[4].data = data04;
    myChart.data.datasets[5].data = data05;
    myChart.data.datasets[6].data = data06;
    myChart.data.datasets[7].data = data07;
    // myChart.data.datasets[4].data = dataMin;
    // myChart.data.datasets[5].data = dataMax;
    myChart.data.labels = labels;
    myChart.options.scales.y= {
    
      // stacked: true,
      // display: true,
      // suggestedMax: maxYaxis,
      min: 0,
      ticks:  { 
        callback: (value, index, values) => {
          return new Intl.NumberFormat("de-DE",{style:"currency", currency:"EUR", maximumFractionDigits: 0}).format(value);
        }
        }
    }
    myChart.options.scales.x = {
      stacked: true,
      display: true,
      ticks: { 
          display: true 
          
      },
      type: 'time',
      time: {
          unit: timerange
      },
      grid: {
        display: false,
        drawBorder: false
    },
    }
    // myChart.options.scales.y1= {
    //   stacked: false,
    //   display: true,
    //   // suggestedMax: maxYaxis,
    //   // grid: {
    //   //   drawOnChartArea: false, // only want the grid lines for one axis to show up
    //   // },
    //   ticks:  { 
    //     callback: (value, index, values) => {
    //       return new Intl.NumberFormat("de-DE",{style:"currency", currency:"EUR", maximumFractionDigits: 0}).format(value);
    //     }
    //     }
    
      
      
    //   }, 
    myChart.update();
  }, [myChart,labels]);

  // if (style === 'normal') 
  return ( 
  // <div
  //   position='relative'
  //   margin='auto'
  //   height= '2000'
  //   width='800vw' 
  //   >

   
  //   <canvas  ref={chartRef} id="myChart"  />
    <canvas   height= '400'  ref={chartRef} id="myChart"  />
   // </div>
  //)

//   if (style === 'mini') return ( 

//     <canvas  width='200'  height= '50' ref={chartRef} id="myChart"  />
    )
 };

export default MixedChart;
