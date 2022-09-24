import React, { useRef, useEffect, useState } from "react";
import {Chart,registerables } from "chart.js";
import ChartDataLabels from 'chartjs-plugin-datalabels';


const PiChart = ({ data,labels,color, rotation}) => {
  
  const chartRef = useRef(null);
  const [myChart, setMyChart] = useState(null);
  
  useEffect(() => {
    if (!chartRef) return;
    Chart.register(...registerables)
    const ctx = chartRef.current.getContext("2d");
    
    // const gradient00 = ctx.createLinearGradient(0, 0, 0, 400);
    // gradient00.addColorStop(0.5, 'rgba(175,61,255,1)');
     
    //let maxYaxis = Math.max(...dataMax)

  
   
    const myChart = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: labels,
        datasets: [
          {
            data: [],
            backgroundColor: color,
            // hoverBackgroundColor: [
            //   color,
            //   "#AAAAAA"
            // ],
            // hoverBorderColor: [
            //   color,
            //   "#ffffff"
            // ]
          },
          
        ]
      },
      plugins: [ChartDataLabels],
      options: {
        plugins: {
          datalabels: {
            formatter: (value, ctx) => {
     
              let datasets = ctx.chart.data.datasets;
     
              if (datasets.indexOf(ctx.dataset) === datasets.length - 1) {
                let sum = datasets[0].data.reduce((a, b) => a + b, 0);
                let percentage = Math.round((value / sum) * 100) + '%';
                return percentage;
              } else {
                return percentage;
              }
            },
            backgroundColor: '#E7FAFC' ,
            color: 'black',
            font: {
              weight: "bold",
              size: 11            },
          },
          tooltip: {
            callbacks: {
              label: function(context){
                var label = context.label,
                    currentValue = context.raw,
                    total = context.chart._metasets[context.datasetIndex].total;
      
                var percentage = parseFloat((currentValue/total*100).toFixed(1));
      
                return label + ": "  + percentage + '%';
              }
            }
          },
          
          legend: {
            display: false,
          },
          title: {
            display: false,
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
        // rotation: (-0.5 * Math.PI) - (-rotation/180 * Math.PI),
        responsive: false,
        // aspectRatio: 1,
        
        cutout: '0%',
        radius: '50',
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

    myChart.data.datasets[0].data = data;
    // myChart.options.elements.center= {
    //   text: `${data[0]}%`,
    // }
 

    myChart.update();
  }, [myChart,data]);

  // if (style === 'normal') 
  return ( 
    
  <canvas  width='150'  height='120' ref={chartRef} id="myChart"  />
    )
 };

export default PiChart;
