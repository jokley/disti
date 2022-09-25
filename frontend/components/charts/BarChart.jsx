import React, { useRef, useEffect, useState } from "react";
import {Chart,registerables } from "chart.js";
import ChartDataLabels from 'chartjs-plugin-datalabels';


const SinglePiChart = ({ bereich1,bereich2,bereich3,labels,needleValue, rotation}) => {
  
  const chartRef = useRef(null);
  const [myChart, setMyChart] = useState(null);

  const color00 = 'rgba(0, 153, 153,1)';
  const color01 = 'rgba(0, 204, 204, 1)';
  const color02 = 'rgba(0, 255, 255, 1)';
  const color03 = 'rgba(153, 255, 255, 1)';
  const color04 = 'rgba(102, 204, 255, 1)';
  const color05= 'rgba(102, 153, 204, 1)';
  const color06 = 'rgba(0, 176, 191  , 1)';
  const color07 = 'rgba(204, 102, 153,1)';
  
  useEffect(() => {
    if (!chartRef) return;
    Chart.register(...registerables)
    const ctx = chartRef.current.getContext("2d");
    
    // const gradient00 = ctx.createLinearGradient(0, 0, 0, 400);
    // gradient00.addColorStop(0.5, 'rgba(175,61,255,1)');
     
    //let maxYaxis = Math.max(...dataMax)

    // const legendFilter = (legendItem, data) => {
    //   let label = data.datasets[legendItem.datasetIndex].label || '';
    //   if (typeof(label) !== 'undefined') {
    //      if (legendItem.datasetIndex >= 10){
    //       return false;
    //     }
    //   }
    //   return label;
    // }

  
   
    const myChart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [
          {
            data: [],
            
          },
          {
            data: [],
            
          },
          
          {
            data: [],
          
          },
          {
            data: [],
            
          },
          {
            data: [],
           
          },
          {
            data: [],
            barThickness: 20,
           
          },

        ]
      },
      // plugins: [ChartDataLabels],
      options: {
        // barPercentage: 1,
        // categoryPercentage: 1.1,
      indexAxis: 'y',

        plugins: {
          // datalabels: {
          //   formatter: (value, ctx) => {
     
          //     let datasets = ctx.chart.data.datasets;
     
          //     if (datasets.indexOf(ctx.dataset) === datasets.length - 1) {
          //       let sum = datasets[0].data.reduce((a, b) => a + b, 0);
          //       let percentage = Math.round((value / sum) * 100) + '%';
          //       return percentage;
          //     } else {
          //       return percentage;
          //     }
          //   },
          //   backgroundColor: '#E7FAFC' ,
          //   align: 'end',
          //   anchor: 'end',
          //   color: 'black',
          //   offset: 8,
          //   font: {
          //     weight: "bold",
          //     size: 11            },
          // },
          legend: {
            display: false,
            // labels: {
            //   filter: legendFilter
            // },
          },
          // tooltip: {
           
          // },
         
          
       
        },
       
        scales: {
          x: { 
            stacked: true, 
             display: true,
             
             min: 10,
              ticks: { 
                  display: true,
                  stepSize: 2,
                  
              },
              grid: {
                  display: false,
                  drawBorder: true,
              },
            
          
          },
          y: {
            stacked: true, 
            display: false,
            ticks: { 
                display: true 
                
                
            },
            grid: {
                display: false,
                drawBorder: false
            },
        
        },
        },
        // elements: {
        //   center: {
        //     text: `0%`,
        //     color: '#FF6384', // Default is #000000
        //     fontStyle: 'Arial', // Default is Arial
        //     maxFontSize: 20, // Default is 25
        //     sidePadding: 20 // Defualt is 20 (as a percentage)
        //   }
        // },
        // rotation: (-0.5 * Math.PI) - (-rotation/160 * Math.PI),
         responsive: false,
        // aspectRatio: 1,
        
        // cutout: '0%',
        // radius: '50',
        //  rotation: 315, // start angle in degrees
        //  circumference:270, // sweep angle in degrees
       
        // tooltips: {
        //   filter: function(item, data) {
        //     var label = data.labels[item.index];
        //     if (label) return item;
        //   }
        // }
      },
      //  plugins: [counter]
    });
    setMyChart(myChart);
  
  }, [chartRef]);





  useEffect(() => {
    if (!myChart) return;

    // console.log(data)
    let zone1 = parseInt(bereich1);
    let zone2 = parseInt(bereich2) + zone1;
    let zone3 =  parseInt(bereich3) + zone2;
    let data1 = [];
    let data2 = [];
    let data3 = [];
    let data4 = [];
    let data5 = [];
    let color1 = 'white';
    let color2 = 'white';
    let color3 = 'white';
    let color4 = 'white';
    let color5 = 'white';
    let color6 = 'white';
    let barThickness1;
    let barThickness2;
    let barThickness3;
    let barThickness4;
    let barThickness5;


    switch(true){
      case (needleValue  >= 0 && needleValue  <= zone1 ) :
            data1=[0,bereich1-(bereich1-needleValue + 0.125)]
            color1 = [color04];
            data2=[0,0.25]
            color2 = [color05];
            barThickness2 = 70;
            data3=[0,bereich1-needleValue-0.125]
            color3 = [color04];
            data4=[0,bereich2]
            color4 = [color06];
            data5=[0,bereich3]
            color5 = [color07];
            color6 = [color04]
            break;
      case (needleValue  >=  zone1 && needleValue  <= zone2) :
            data1=[0,bereich1]
            color1 = [color04];
            data2=[0,bereich2-(zone2-needleValue + 0.125)]
            color2 = [color06];
            data3=[0,0.25]
            color3 = [color05];
            barThickness3 = 70;
            data4=[0,zone2-needleValue -0.125]
            color4 = [color06];
            data5=[0,bereich3]
            color5 = [color07];
            color6 = [color06]
            break;
      case (needleValue  >= zone2 && needleValue  <= zone3 ) :
            data1=[0,bereich1]
            color1 = [color04];
            data2=[0,bereich2]
            color2 = [color06];
            data3=[0 ,bereich3-(zone3-needleValue + 0.125)]
            color3 = [color07];
            data4=[0,0.25]
            color4 = [color05];
            barThickness4 = 70;
            data5=[0,zone3-needleValue+0.125]
            color5 = [color07];
            color6 = [color07]
            break;
      
  }

    myChart.data.datasets[0].data = data1;
    myChart.data.datasets[1].data = data2;
    myChart.data.datasets[2].data = data3;
    myChart.data.datasets[3].data = data4;
    myChart.data.datasets[4].data = data5;
    myChart.data.datasets[5].data = [needleValue,0];



    myChart.data.datasets[0].backgroundColor = color1;
    myChart.data.datasets[1].backgroundColor = color2;
    myChart.data.datasets[2].backgroundColor = color3;
    myChart.data.datasets[3].backgroundColor = color4;
    myChart.data.datasets[4].backgroundColor = color5;
    myChart.data.datasets[5].backgroundColor = color6;


    myChart.data.datasets[0].barThickness = barThickness1;
    myChart.data.datasets[1].barThickness = barThickness2;
    myChart.data.datasets[2].barThickness = barThickness3;
    myChart.data.datasets[3].barThickness = barThickness4;
    myChart.data.datasets[4].barThickness = barThickness5;

    

    // myChart.data.labels = labels;
    // myChart.options.elements.center= {
    //   text: `${data[0]}%`,
    // }
    // myChart.options.scales.x= {
    //  stacked: true,
    // }
    // myChart.options.scales.y= {
    //   stacked: true,
    //  }
 

    myChart.update();
  }, [myChart,needleValue]);

  // if (style === 'normal') 
  return ( 
    
  <canvas  width='450'  height='120' ref={chartRef} id="myChart"  />
    )
 };

export default SinglePiChart;
