import React, { useRef, useEffect, useState } from "react";
import {Chart,registerables } from "chart.js";



const StackedDoughnut = ({ data0,data1,data2,data3,data4,data5,data6,data7,labels,color0,color1,color2,color3,color4,color5,color6,color7}) => {
  
  const chartRef = useRef(null);
  const [myChart, setMyChart] = useState(null);
  
  useEffect(() => {
    if (!chartRef) return;
    Chart.register(...registerables)
    const ctx = chartRef.current.getContext("2d");
    
    const counter = {
      id: 'counter',
      beforeDraw (chart, args, options) {
  
         if (chart.config.options.elements.center) {
        //   //Get ctx from string
          // var ctx = chart.chart.ctx;
          // var ctx = chart.ctx;

        //  const {ctx} = chart;
        //  ctx.save();
  
          //Get options from the center object in options
          var centerConfig = chart.config.options.elements.center;
          var fontStyle = centerConfig.fontStyle || 'Arial';
          var txt = centerConfig.text;
          var color = centerConfig.color || '#000';
          var maxFontSize = centerConfig.maxFontSize || 25;
          var sidePadding = centerConfig.sidePadding || 20;
          var sidePaddingCalculated = (sidePadding / 100) * (chart.innerRadius * 2)
          //Start with a base font of 30px
          ctx.font = "20px " + fontStyle;
  
          //Get the width of the string and also the width of the element minus 10 to give it 5px side padding
          var stringWidth = ctx.measureText(txt).width;
          var elementWidth = (chart.innerRadius * 2) - sidePaddingCalculated;
  
          // Find out how much the font can grow in width.
          var widthRatio = elementWidth / stringWidth;
          var newFontSize = Math.floor(30 * widthRatio);
          var elementHeight = (chart.innerRadius * 2);
  
          // Pick a new font size so it will not be larger than the height of label.
          var fontSizeToUse = Math.min(newFontSize, elementHeight, maxFontSize);
  
          //Set font settings to draw it correctly.
          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';
          var centerX = ((chart.chartArea.left + chart.chartArea.right) / 2);
          var centerY = ((chart.chartArea.top + chart.chartArea.bottom) / 2);
          ctx.font = fontSizeToUse + "px " + fontStyle;
          ctx.fillStyle = color;
  
          //Draw text in center
          ctx.fillText(txt, centerX, centerY);
         }
      }
    };

  
   
    const myChart = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: labels,
        datasets: [
          {
            data: [],
            backgroundColor: color0,
          },
          {
            data: [],
            backgroundColor: color1,
          },
          {
            data: [],
            backgroundColor: color2,
          },
          {
            data: [],
            backgroundColor: color3,
          },
          {
            data: [],
            backgroundColor: color4,
          },
          {
            data: [],
            backgroundColor: color5,
          },
          {
            data: [],
            backgroundColor: color6,
          },
          {
            data: [],
            backgroundColor: color7,
          }
          
        ]
      },
      options: {
        plugins: {
          tooltip: {
            callbacks: {
              label: function(context){
                var label = context.label,
                    currentValue = context.raw,
                    total = context.chart._metasets[context.datasetIndex].total;
      
                var percentage = parseFloat((currentValue/total*100).toFixed(1));
      
                return label + "-" + context.datasetIndex + ": "  + percentage + '%';
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
        
        cutout: '10%',
        radius: '75',
        //  rotation: 315, // start angle in degrees
        circumference:270, // sweep angle in degrees
       
        // tooltips: {
        //   filter: function(item, data) {
        //     var label = data.labels[item.index];
        //     if (label) return item;
        //   }
        // }
      },
        // plugins: [counter],
    });
    setMyChart(myChart);
  
  }, [chartRef]);





  useEffect(() => {
    if (!myChart) return;

    // let sumValues = data[0]+data[1];
    // let max = data[2];
    // let percent = Math.round(sumValues*100/max)



    myChart.data.datasets[0].data = data0
    myChart.data.datasets[1].data = data1;
    myChart.data.datasets[2].data = data2;
    myChart.data.datasets[3].data = data3;
    myChart.data.datasets[4].data = data4;
    myChart.data.datasets[5].data = data5;
    myChart.data.datasets[6].data = data6;
    myChart.data.datasets[7].data = data7;



   
    // myChart.options.elements.center= {
    //   text: `${percent}%`,
    // }
 

    myChart.update();
  }, [myChart,data0]);

  // if (style === 'normal') 
  return ( 
    
  <canvas  width='150'  height='120' ref={chartRef} id="myChart"  />
    )
 };

export default StackedDoughnut;
