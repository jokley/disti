import React, { useRef, useEffect, useState } from "react";
import {Chart,registerables } from "chart.js";



const GaugeChart = ({ data,data1,needleValue,labels,color,color1, maxValue}) => {
  
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

    const needle = {
      id: 'needle',
    afterDraw (chart)  {
      var needleValue = chart.config.data.datasets[0].needleValue;
      var dataTotal = chart.config.data.datasets[0].data.reduce((a, b) => a + b, 0);
      var angle = Math.PI + (1 / dataTotal * needleValue * Math.PI);
      var ctx = chart.ctx;
      var cw = chart.canvas.offsetWidth;
      var ch = chart.canvas.offsetHeight;
      var cx = cw / 2;
      var cy = ch - 6;

      ctx.translate(cx, cy);
      ctx.rotate(angle);
      ctx.beginPath();
      ctx.moveTo(0, -3);
      ctx.lineTo(ch - 20, 0);
      ctx.lineTo(0, 3);
      ctx.fillStyle = 'rgb(100, 100, 100)';
      ctx.fill();
      ctx.rotate(-angle);
      ctx.translate(-cx, -cy);
      ctx.beginPath();
      ctx.arc(cx, cy, 5, 0, Math.PI * 2);
      ctx.fill();
    }
  }
    
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
          var centerY = ((chart.chartArea.top + chart.chartArea.bottom)/ 1.5);
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
            backgroundColor: color1,
            weight: 1,
          },
          {
            data: [],
            needleValue: 0,
            backgroundColor: color,
            weight: 2,
          },
          
        ]
      },
      options: {
        plugins: {
          // tooltip: {
          //   callbacks: {
          //     label: function(context){
          //       var label = context.label,
          //           currentValue = context.raw,
          //           total = context.chart._metasets[context.datasetIndex].total;
      
          //       var percentage = parseFloat((currentValue/total*100).toFixed(1));
      
          //       return label + ": "  + percentage + '%';
          //     }
          //   }
          // },
       
         
          legend: {
            display: false,
          },
          title: {
            display: false,
          },
        },
        elements: {
          center: {
            text: `0%`,
            color: '#FF6384', // Default is #000000
            fontStyle: 'Arial', // Default is Arial
            maxFontSize: 20, // Default is 25
            sidePadding: 20 // Defualt is 20 (as a percentage)
          }
        },
        // rotation: (-0.5 * Math.PI) - (-rotation/180 * Math.PI),
         responsive: false,
        // aspectRatio: 1,
        
        // cutout: '40%',
        // radius: '75',
           
        // rotation: -Math.PI,
        cutoutPercentage: 30,
        // circumference: Math.PI,
        
          rotation: 270, // start angle in degrees
           circumference:180, // sweep angle in degrees
       
        // tooltips: {
        //   filter: function(item, data) {
        //     var label = data.labels[item.index];
        //     if (label) return item;
        //   }
        // }
      },
         plugins: [counter,needle],
    });
    setMyChart(myChart);
  
  }, [chartRef]);





  useEffect(() => {
    if (!myChart) return;

    // let sumValues = data[0]+data[1];
    // let percent = Math.round(sumValues*100/maxValue)
    let color = color

    switch(true){
      case (needleValue < 70):
          color = [color04,'white'];
          break;
      case  (needleValue >=70 &&  needleValue <80):
        color = [color07,'white'];
          break;
      case  (needleValue >=80 &&  needleValue < 90):
        color = [color06,'white'];
          break;
      case  (needleValue >=90 ):
        color = [color05,'white'];
          break;
      
  }




    myChart.data.datasets[0].data = data1;
    myChart.data.datasets[1].data = data;
    myChart.data.datasets[0].needleValue = needleValue;
    myChart.data.datasets[0].backgroundColor = color
    
    myChart.options.elements.center= {
      text: `${needleValue}°`,
    }
 

    myChart.update();
  }, [myChart,data]);

  // if (style === 'normal') 
  return ( 
    
  <canvas  width='300'  height='120' ref={chartRef} id="myChart"  />
    )
 };

export default GaugeChart;
