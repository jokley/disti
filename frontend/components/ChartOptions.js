export const options = {
    elements: {
        point:{
            radius: 0
        }
    },
    legend: {
        display: false
    },
    responsive: true,
    maintainAspectRatio: false,
    scales: {
        xAxes: [{
            //type: 'time',
            //distrubution: 'linear',
            ticks: { 
                display: true 
            },
            gridLines: {
                display: false,
                drawBorder: false
            },
            //  time: {
            //      tooltipFormat: 'HH:mm',
            //      unit: 'minute',
            //      autoSkip: true,
            //      source: 'labels',
            //      stepSize: 10,
            //     displayFormats: {
            //         'minute': 'HH:mm',
            //         'hour': 'HH:mm'
            //     },
            // }
        }],
        yAxes: [{
            ticks: { 
                display: true,
                min: 0,
              	max: 100,
              	stepSize: 25 
            },
            gridLines: {
                display: true,
                drawBorder: true
            }
        }]
    }
  }

  export const options_simple = {
    elements: {
        point:{
            radius: 0
        }
    },
    legend: {
        display: false
    },
    responsive: false,
    maintainAspectRatio: false,
    scales: {
        xAxes: [{
            //type: 'time',
            //distrubution: 'linear',
            ticks: { 
                display: false 
            },
            gridLines: {
                display: false,
                drawBorder: false
            },
            //  time: {
            //      tooltipFormat: 'HH:mm',
            //      unit: 'minute',
            //      autoSkip: true,
            //      source: 'labels',
            //      stepSize: 10,
            //     displayFormats: {
            //         'minute': 'HH:mm',
            //         'hour': 'HH:mm'
            //     },
            // }
        }],
        yAxes: [{
            ticks: { 
                display: false,
                //min: 0,
              	//max: 100,
              	//stepSize: 100
            },
            gridLines: {
                display: false,
                drawBorder: false
            }
        }]
    }
  }

