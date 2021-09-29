import React, { useRef, useEffect, useState } from "react";
import Chart from "chart.js";


const ExmapleChart = ({ label, data,labels,options }) => {
  
  const chartRef = useRef(null);
  const [myChart, setMyChart] = useState(null);
  
  useEffect(() => {
    if (!chartRef) return;
    const ctx = chartRef.current.getContext("2d");
    const gradient = ctx.createLinearGradient(0, 0, 0, 450);
    // ctx.canvas.parentNode.style.width = "80vh";
    // ctx.canvas.parentNode.style.height = "20vh";


    gradient.addColorStop(0, 'rgba(20, 120,175, 0.5)');
    gradient.addColorStop(0.5, 'rgba(20, 120, 175, 0.25)');
    gradient.addColorStop(1, 'rgba(20, 120, 175, 0.125)');


    const myChart = new Chart(ctx, {
      type: "line", 
      data: {
        labels: labels,
        datasets: [
          {
            label: label,
            data: [],
            fill: false,
            //backgroundColor: 'white',
            borderColor: gradient,
            borderWidth: 5
          }
        ]
      },
      options: options,
    });
    setMyChart(myChart);
  
  }, [chartRef,options, labels]);

  useEffect(() => {
    if (!myChart) return;
    myChart.data.datasets[0].data = data;
    myChart.update();
  }, [data,myChart]);

  return (
    <div
    position='relative'
    margin='auto'
    height= '20vh'
    width='80vw' >
    <canvas ref={chartRef} id="myChart"  />
  </div>
  )
};

export default ExmapleChart;
