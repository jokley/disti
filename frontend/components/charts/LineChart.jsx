import React, { useRef, useEffect, useState } from "react";
import {Chart,registerables } from "chart.js";
import 'chartjs-adapter-moment';
import ChartDataLabels from 'chartjs-plugin-datalabels';


const LineChart = ({ data,labels,label,color}) => {
  
  const chartRef = useRef(null);
  const [myChart, setMyChart] = useState(null);
  
  useEffect(() => {
    if (!chartRef) return;
    Chart.register(...registerables)
    const ctx = chartRef.current.getContext("2d");
    
    const gradient01 = ctx.createLinearGradient(0, 0, 0, 400);
    gradient01.addColorStop(0.75, 'rgba(47, 213, 180 ,0.15)');
    gradient01.addColorStop(0.5, 'rgba(47, 213, 180 ,0.35)');
    gradient01.addColorStop(0.25, 'rgba(47, 213, 180 ,0.75)');

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
    

  
   
    const myChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [
          {
            data: [],
            label: label,
            fill: true,
            borderColor: 'rgb(75, 192, 192)',
            backgroundColor: gradient01,
            // tension: 0.1,
            borderWidth: 2,
      }
    ]
  },
  plugins: [cursor],
  options: {
    // responsive: false,
    elements: {
      point:{
          radius: 0
      }
    },
    plugins: {
      datalabels: {
        display: false,
      },
      tooltip: {
              mode: 'index',
              intersect: false,
      //         callbacks: {
      //                     label: function(context) {
      //                         let label = context.dataset.label || '';

      //                         if (label) {
      //                             label += ': ';
      //                         }
      //                         if (context.parsed.y !== null) {
      //                             label += new Intl.NumberFormat('de-DE', {maximumFractionDigits: 1 }).format(context.parsed.y);
      //                         }
      //                         return label;
      //                     },
      // //                     footer: footer,  
      //         },
              
            
              },
          hover: {
                mode: 'nearest',
                intersect: false
                }
   
          },
}
    
  
    });
    setMyChart(myChart);
  
  }, [chartRef]);





  useEffect(() => {
    if (!myChart) return;

    // console.log(data)

    myChart.data.datasets[0].data = data;
    myChart.data.labels = labels;
    // myChart.options.elements.center= {
    //   text: `${data[0]}%`,
    // }
 

    myChart.update();
  }, [myChart,data]);

  return ( 
    
  <canvas  width='900'  height='200' ref={chartRef} id="myChart"  />
    )
 };

export default LineChart;
