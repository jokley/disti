import React, { useRef, useEffect, useState } from "react";
import Chart from "chart.js";


const ExmapleChart = ({ label, data,labels,options }) => {
  
  const chartRef = useRef(null);
  const [myChart, setMyChart] = useState(null);
  
  useEffect(() => {
    if (!chartRef) return;
    const ctx = chartRef.current.getContext("2d");
    const gradient = ctx.createLinearGradient(0, 0, 0, 450);


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

  return <canvas ref={chartRef} id="myChart" position="relative" height="150vh" width="300vw"  />;
};

export default ExmapleChart;
